"""Classify archived PR742 native results without repairing or exporting a task."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'inputs-private/macs-742-native-001'
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    receipt = json.loads((ROOT / 'macs-742-native-readback-001.json').read_text())
    manifest = json.loads((ROOT / 'macs-native-742-manifest.json').read_text())
    assert receipt['record_verified'] and receipt['owned_containers_absent'] and receipt['tools_removed']
    assert not receipt['cleanup_errors'] and receipt['retained_image'] == manifest['image_tag']
    assert [arm['name'] for arm in receipt['arms']] == ['original', 'rebuild']
    report = json.loads((RAW / 'comparison.json').read_text())
    rows = []
    for arm in report['arms']:
        name = arm['name']
        outcome_path = RAW / name / 'outcome.json'
        outcome = json.loads(outcome_path.read_text()) if outcome_path.exists() else None
        stages = []
        for index, call in enumerate(arm.get('calls', [])):
            stage = call.get('stage')
            if not stage:
                continue
            path = RAW / name / f'call-{index:02d}-stdout.txt'
            if not path.exists():
                stages.append({'stage': stage, 'call_index': index, 'output_present': False, 'outer_exit_code': call.get('exit_code')})
                continue
            assert sha(path) == call['stdout_sha256']
            output = ANSI.sub('', path.read_text(errors='replace'))
            statuses = re.findall(r'^\S.*?::\S+\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b', output, re.M)
            summary = re.findall(r'^=+\s*(.{1,250}?)\s+in\s+[0-9.]+s\s*=+$', output, re.M)
            stages.append({
                'stage': stage, 'call_index': index, 'output_present': True,
                'outer_exit_code': call.get('exit_code'), 'duration_seconds': call.get('duration_sec'),
                'start_marker': 'R2E_START_TEST_OUTPUT' in output,
                'end_marker': 'R2E_END_TEST_OUTPUT' in output,
                'collection_error_marker_count': output.count('ERROR collecting'),
                'reported_status_lines': {status: statuses.count(status) for status in sorted(set(statuses))},
                'pytest_summary': summary[-1] if summary else None,
                'stale_extension_spec_error': 'AttributeError: __spec__' in output,
                'missing_module_error': bool(re.search(r'ModuleNotFoundError|No module named', output)),
            })
        rows.append({
            'name': name, 'state': arm['state'], 'reason': arm.get('reason'),
            'validator_status': outcome['status'] if outcome else None,
            'validator_reason': outcome['reason'] if outcome else None,
            'fail_to_pass': outcome['fail_to_pass'] if outcome else [],
            'pass_to_pass_count': len(outcome['pass_to_pass']) if outcome else 0,
            'stages': stages,
        })
    native_pair_reported = any(row['name'] == 'rebuild' and row['validator_status'] == 'verified' and row['fail_to_pass'] for row in rows)
    result = {
        'scope': 'Frozen PR742 native original-versus-opt-in-rebuild comparison; no task repair or regrading',
        'archive_sha256': receipt['archive_sha256'], 'image_id': manifest['image_id'],
        'source_patch_sha256': sha(ROOT / 'inputs-private/macs-native-742/source.patch'),
        'test_patch_sha256': sha(ROOT / 'inputs-private/macs-native-742/test.patch'),
        'arms': rows, 'native_f2p_pair_reported': bool(native_pair_reported),
        'exported_task': False, 'independent_controls_run': 0, 'model_calls': 0,
        'allocated_cpu_hours': receipt['allocated_cpu_hours'],
        'limits': [
            'Upstream native stage outer exit can mask inner pytest failure; inspect archived summaries and collection errors',
            'Native F2P/P2P alone does not establish exported reward or independent nop/oracle controls',
            'Image was reconstructed from recorded actions; mutable dependencies may differ from original run',
        ],
    }
    (ROOT / 'macs-742-native-diagnosis.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('arms', 'limits')}))


if __name__ == '__main__':
    main()
