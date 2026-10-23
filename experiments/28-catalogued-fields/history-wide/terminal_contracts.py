"""Extract original terminal ref/contract metadata for notice preparation; no execution."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    assert args.slug in {r['slug'] for r in json.loads((ROOT.parent / 'cohort.json').read_text())}
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    source = args.state_dir / (run + '-results')
    phase = source / 'phase-artifacts.tar.gz'
    records, originals, starts, total = {}, {}, [], 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            total += member.size
            assert total < 32 * 1024**2
            if not (member.name.endswith('/events.jsonl') or '/discovery-pr-' in member.name
                    or member.name.startswith('outputs/')):
                continue
            assert member.size < 4 * 1024**2
            raw = archive.extractfile(member).read()
            originals[member.name] = hashlib.sha256(raw).hexdigest()
            decoded = gzip.decompress(raw) if member.name.endswith('.gz') else raw
            assert len(decoded) < 8 * 1024**2
            records[member.name] = decoded
            if member.name.endswith('/events.jsonl'):
                starts.extend((Path(member.name).parts[1], row) for row in map(json.loads, decoded.decode().splitlines())
                    if row['event'] == 'validation_start')
    refs, contracts = [], []
    for batch, event in starts:
        name = f"native-observations/{batch}/discovery-pr-{event['pr']}.json.gz"
        refs.append({'batch': batch, 'event': event, 'head_ref': json.loads(records[name])['headRefOid'],
            'descriptor_original_gzip_sha256': originals[name]})
    for name, raw in records.items():
        if not name.startswith('outputs/') or not name.endswith('/task.toml'):
            continue
        prefix = name.removesuffix('task.toml')
        value = tomllib.loads(raw.decode()); meta = value['metadata']['repo2env']
        contracts.append({'task': Path(name).parent.name, 'task_toml_sha256': originals[name],
            'provenance': {k: meta.get(k) for k in ['pipeline', 'pipeline_version', 'repo', 'ref', 'reference', 'source_access', 'synthesis_llm']},
            'agent': value['agent'], 'verifier': value['verifier'],
            'test_script_sha256': originals[prefix + 'tests/test.sh'],
            'patch_paths': sorted(set(re.findall(r'^diff --git a/.*? b/(.*?)$', records[prefix + 'tests/test.sh'].decode(), re.M))),
            'f2p_count': len(json.loads(records[prefix + 'tests/f2p.json'])),
            'p2p_count': len(json.loads(records[prefix + 'tests/p2p.json']))})
    ledger_path = source / 'history-batches.json'
    ledger = json.loads(ledger_path.read_text())
    output = ROOT / 'live-observations'
    snapshot = {'run_id': run, 'native_state': ledger['state'],
        'scope': 'Metadata extracted from the completed original phase; not a prior live observation or independent execution. No data payload, tests, models, retries or repairs.',
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_phase_sha256': hashlib.sha256(phase.read_bytes()).hexdigest(),
        'validation_ref_uses': refs, 'task_contracts': sorted(contracts, key=lambda x: x['task'])}
    (output / (args.slug + '-terminal-contracts.json')).write_text(json.dumps(snapshot, indent=2) + '\n')
    (output / (args.slug + '-terminal-ledger.json')).write_text(json.dumps({'run_id': run,
        'native_ledger': ledger, 'original_native_ledger_sha256': hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        'scope': 'Original terminal native ledger, not a prior live snapshot.'}, indent=2) + '\n')
    print(json.dumps({'slug': args.slug, 'validation_starts': len(refs),
        'unique_refs': len({ref for row in refs for ref in [row['event']['base_commit'], row['head_ref']]}), 'contracts': len(contracts)}))


if __name__ == '__main__':
    main()
