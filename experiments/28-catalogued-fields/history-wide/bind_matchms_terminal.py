"""Bind already observed Matchms metadata to original terminal bytes, without execution."""

from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parent
STATE = Path('/home/exedev/.local/share/biotasks/checkpoints/issue28-history-wide-20261022')
SOURCE = STATE / 'biotasks28-history-matchms-matchms-001-results'


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    phase = SOURCE / 'phase-artifacts.tar.gz'
    live_names = {
        'completed': 'matchms-native-completed-20261023T044032Z.json',
        'contracts': 'matchms-native-contracts-20261023T050335Z.json',
        'files': 'matchms-export-files-20261023T042434Z.json',
        'first_pair': 'matchms-first-pair-20261023T040256Z.json',
        'bootstrap': 'matchms-bootstrap-detail-20261023T040408Z.json',
    }
    live = {k: read(ROOT / 'live-observations' / v) for k, v in live_names.items()}
    hashes, decoded, signal_rows, outcomes = {}, {}, [], {}
    expanded = 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            expanded += member.size
            assert expanded <= 16 * 1024**2
            raw = archive.extractfile(member).read()
            hashes[member.name] = sha(raw)
            if member.name.endswith('.gz'):
                raw = gzip.decompress(raw)
            assert len(raw) < 16 * 1024**2
            # Store only bounded metadata. Never put spectrum payloads into reports.
            if (member.name.endswith('/events.jsonl') or '/discovery-pr-' in member.name
                    or member.name.endswith('bootstrap.json') or member.name.endswith('validation-001-pr-966.json.gz')):
                decoded[member.name] = raw
            if '/validation-' in member.name:
                value = json.loads(raw)
                outcomes[member.name] = {k: value[k] for k in ['status', 'reason']}
                outcomes[member.name].update(f2p=len(value['fail_to_pass']), p2p=len(value['pass_to_pass']))
            for hit in re.finditer(rb'[A-Za-z0-9+/]{4096,}={0,2}', raw):
                assert re.search(rb'<(?:binary|peaks)[^>]*>\s*$', raw[max(0, hit.start()-200):hit.start()])
                signal_rows.append({'member': member.name, 'encoded_bytes': hit.end()-hit.start(),
                    'encoded_sha256': sha(hit.group()), 'classification': 'XML mass-spectrum binary-array fixture, original PR110 patch; lineage/terms unresolved. Restricted retention only.'})
    completed = live['completed']
    for remote, expected in completed['original_source_sha256'].items():
        relative = remote.removeprefix('/work/')
        original = (SOURCE / relative.removeprefix('evidence/')).read_bytes() if relative.startswith('evidence/') else None
        assert (sha(original) if original is not None else hashes[relative]) == expected
    assert read(SOURCE / 'history-batches.json') == completed['native_ledger']
    assert read(SOURCE / 'exported-tasks.json') == completed['original_export_manifest']
    outcome_count = 0
    for batch, observation in completed['observations'].items():
        for row in observation['validations']:
            names = [name for name in outcomes if name.startswith('native-observations/' + batch + '/')
                and name.endswith('-pr-' + str(row['pr']) + '.json.gz')]
            assert len(names) == 1 and hashes[names[0]] == row['original_gzip_sha256']
            assert outcomes[names[0]] == {k: row[k] for k in ['status', 'reason', 'f2p', 'p2p']}
            outcome_count += 1
    assert outcome_count == len(outcomes) == 164
    starts = {}
    for name, raw in decoded.items():
        if name.endswith('/events.jsonl'):
            for event in map(json.loads, raw.decode().splitlines()):
                if event['event'] == 'validation_start':
                    starts[(Path(name).parts[1], event['validation'], event['pr'])] = event
    for row in live['contracts']['validation_ref_uses']:
        event = row['event']; batch = row['batch']
        assert starts[(batch, event['validation'], event['pr'])] == event
        matches = [name for name in hashes if name.startswith('native-observations/' + batch + '/')
            and '/discovery-pr-' + str(event['pr']) + '.' in name]
        assert len(matches) == 1
        assert hashes[matches[0]] == row['descriptor_original_gzip_sha256']
        assert json.loads(decoded[matches[0]])['headRefOid'] == row['head_ref']
    assert len(starts) == len(live['contracts']['validation_ref_uses']) == 174
    inventory = read(SOURCE / 'fresh-task-files-unchanged.json')
    assert inventory['verified'] and inventory['before'] == inventory['after']
    for row in live['contracts']['task_contracts']:
        task_path = '/work/outputs/matchms__matchms/' + row['task']
        assert inventory['before'][task_path]['task.toml'] == row['task_toml_sha256']
    for task in live['files']['exported_task_directories']:
        assert {name: row['sha256'] for name, row in task['files'].items()} == inventory['before'][task['path']]
    for row in live['first_pair']['original_returned_outcomes']:
        name = row['path'].removeprefix('/work/')
        assert hashes[name] == row['original_gzip_sha256']
        outcome = json.loads(decoded[name])
        for stage in ['pre', 'post']:
            assert sha(outcome[stage + '_log'].encode()) == row['stages'][stage]['log_sha256']
    for row in live['bootstrap']['bootstrap_records']:
        assert hashes[row['path'].removeprefix('/work/')] == row['sha256']
    descriptor = live['bootstrap']['pr966_descriptor']
    assert hashes[descriptor['path'].removeprefix('/work/')] == descriptor['original_gzip_sha256']
    notice_path = ROOT / 'source-notices/matchms__matchms/notice-inventory-native-completed-20261023.json'
    notices = read(notice_path)
    actual_refs = Counter((ref, event['pr'], role, batch, validation)
        for (batch, validation, _), event in starts.items()
        for role, ref in [('base', event['base_commit']), ('head', next(row['head_ref'] for row in live['contracts']['validation_ref_uses']
            if row['batch'] == batch and row['event']['validation'] == validation))])
    notice_refs = Counter((row['ref'], use['pr'], use['role'], use['batch'], use['validation'])
        for row in notices['source_notices'] for use in row['uses_in_original_validation_records'])
    assert actual_refs == notice_refs
    for row in notices['source_notices']:
        raw = (notice_path.parent / row['path']).read_bytes()
        assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Original terminal-byte reconciliation only; no model, build, test, repair, native retry or reward changes.',
        'source_sha256': sha(Path(__file__).read_bytes()), 'original_phase_sha256': sha(phase.read_bytes()),
        'live_snapshot_sha256': {k: sha((ROOT / 'live-observations' / v).read_bytes()) for k, v in live_names.items()},
        'completed_ledger_event_candidate_export_hashes_verified': len(completed['original_source_sha256']),
        'completed_outcome_original_gzip_hashes_and_headers_verified': outcome_count,
        'validation_start_descriptor_pairs_verified': len(starts), 'terminal_task_contracts_verified': len(live['contracts']['task_contracts']),
        'earlier_export_file_inventories_verified': len(live['files']['exported_task_directories']),
        'first_pair_original_gzip_and_stage_log_hashes_verified': True, 'bootstrap_original_bytes_verified': True,
        'all_before_after_task_files_unchanged': True, 'source_notices_verified': len(notices['source_notices']),
        'source_notice_inventory_sha256': sha(notice_path.read_bytes()), 'notice_ref_uses_verified': sum(actual_refs.values()),
        'encoded_fixture_signals': signal_rows,
        'retention': 'Private evidence only: actual restricted and unresolved spectrum-data terms; software Apache-2.0 notices do not override data terms.'}
    (ROOT / 'results/matchms__matchms-terminal-bindings.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['live_snapshot_sha256', 'encoded_fixture_signals']}))


if __name__ == '__main__':
    main()
