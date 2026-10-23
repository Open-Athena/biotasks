"""Bind original observed refs/contracts/notices to terminal bytes without execution."""

import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--slug', required=True)
    parser.add_argument('--contracts', required=True, type=Path)
    parser.add_argument('--ledger', required=True, type=Path)
    parser.add_argument('--notices', required=True, type=Path)
    args = parser.parse_args()
    assert args.slug in {r['slug'] for r in read(ROOT.parent / 'cohort.json')}
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    source = args.state_dir / (run + '-results')
    contracts, ledger, notices = map(read, [args.contracts, args.ledger, args.notices])
    assert contracts['run_id'] == ledger['run_id'] == run
    phase = source / 'phase-artifacts.tar.gz'
    assessment = read(ROOT / 'results' / (args.slug + '.json'))
    assert sha(phase.read_bytes()) == assessment['original_phase_sha256']
    raw_ledger = (source / 'history-batches.json').read_bytes()
    assert sha(raw_ledger) == ledger['original_native_ledger_sha256']
    assert json.loads(raw_ledger) == ledger['native_ledger']
    before = read(source / 'fresh-task-files-unchanged.json')
    assert before['verified'] and before['before'] == before['after']
    raw_files, decoded, starts, expanded, stored = {}, {}, {}, 0, 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            expanded += member.size
            assert expanded < 32 * 1024**2
            raw = archive.extractfile(member).read()
            if not (member.name.endswith('/events.jsonl') or '/discovery-pr-' in member.name
                    or member.name.startswith('outputs/')):
                continue
            stored += len(raw)
            assert stored < 16 * 1024**2
            raw_files[member.name] = raw
            value = gzip.decompress(raw) if member.name.endswith('.gz') else raw
            assert len(value) < 4 * 1024**2
            decoded[member.name] = value
            if member.name.endswith('/events.jsonl'):
                for event in map(json.loads, value.decode().splitlines()):
                    if event['event'] == 'validation_start':
                        starts[(Path(member.name).parts[1], event['validation'], event['pr'])] = event
    uses = Counter()
    assert len(starts) == len(contracts['validation_ref_uses'])
    for row in contracts['validation_ref_uses']:
        event, batch = row['event'], row['batch']
        assert starts[(batch, event['validation'], event['pr'])] == event
        descriptor = f"native-observations/{batch}/discovery-pr-{event['pr']}.json.gz"
        assert sha(raw_files[descriptor]) == row['descriptor_original_gzip_sha256']
        assert json.loads(decoded[descriptor])['headRefOid'] == row['head_ref']
        for role, ref in [('base', event['base_commit']), ('head', row['head_ref'])]:
            uses[(ref, event['pr'], role, batch, event['validation'])] += 1
    for row in contracts['task_contracts']:
        prefix = 'outputs/' + args.slug + '/' + row['task'] + '/'
        assert sha(raw_files[prefix + 'task.toml']) == row['task_toml_sha256']
        assert sha(raw_files[prefix + 'tests/test.sh']) == row['test_script_sha256']
        config = tomllib.loads(decoded[prefix + 'task.toml'].decode())
        meta = config['metadata']['repo2env']
        assert row['provenance'] == {k: meta.get(k) for k in row['provenance']}
        assert row['agent'] == config['agent'] and row['verifier'] == config['verifier']
        for name in ['f2p', 'p2p']:
            assert len(json.loads(decoded[prefix + 'tests/' + name + '.json'])) == row[name + '_count']
    assert len(contracts['task_contracts']) == len(before['before']) == assessment['native_exports_manifest_present']
    for original, files in before['before'].items():
        prefix = original.removeprefix('/work/') + '/'
        assert all(sha(raw_files[prefix + name]) == digest for name, digest in files.items())
    notice_uses = Counter((row['ref'], use['pr'], use['role'], use['batch'], use['validation'])
        for row in notices['source_notices'] for use in row['uses_in_original_validation_records'])
    assert uses == notice_uses and not notices['unfetched_refs_at_walltime_boundary']
    for row in notices['source_notices']:
        assert not row.get('unavailable')
        raw = (args.notices.parent / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Original terminal source/contract/notice/task-byte binding only; no tests, models, repair, retry, new grades or data-use clearance.',
        'source_sha256': sha(Path(__file__).read_bytes()), 'original_phase_sha256': assessment['original_phase_sha256'],
        'input_snapshot_sha256': {str(p): sha(p.read_bytes()) for p in [args.contracts, args.ledger, args.notices]},
        'original_completed_native_ledger_bytes_verified': True,
        'validation_start_descriptor_pairs_verified': len(starts),
        'all_exported_contracts_verified': len(contracts['task_contracts']),
        'all_original_before_after_task_files_unchanged': True,
        'source_notices_verified': len(notices['source_notices']), 'source_notice_ref_uses_verified': sum(uses.values())}
    (ROOT / 'results' / (args.slug + '-terminal-bindings.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
