"""Independently reconcile converted grades against frozen native control inputs."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(summary, inputs):
    manifest = json.loads((inputs / 'manifest.json').read_text())
    assert summary['marin_revision'] == manifest['marin_revision']
    assert summary['model_calls'] == manifest['model_calls'] == 0
    expected = {x['pr']: x for x in manifest['records']}
    rows = summary['records']
    assert len(rows) == len(expected) and {x['pr'] for x in rows} == set(expected)
    results = []
    for record in rows:
        pr = record['pr']
        frozen = expected[pr]
        controls_file = inputs / frozen['control_inputs']
        raw = controls_file.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest['files'][frozen['control_inputs']]['sha256']
        controls = json.loads(raw)['cases']
        assert len(record['cases']) == len(controls) == 6
        expected_cases = {x['case']: x for x in controls}
        assert {x['case'] for x in record['cases']} == set(expected_cases)
        assert record['schema_validated'] and record['runtime_parity']
        assert record['stage'] == 'paired_native_Marin_controls_passed'
        case_rows = []
        for case in record['cases']:
            saved = expected_cases[case['case']]
            assert case['solution_sha256'] == saved['solution_sha256']
            expected_reward = saved['expected_reward']
            assert case['expected_reward'] == expected_reward
            assert case['marin_result']['status'] == 'graded'
            assert case['marin_result']['error'] is None
            assert case['native_reward'] == case['marin_reward'] == case['marin_result']['reward']
            assert case['native_details'] == case['marin_details']
            assert case['native_details']['parse_status'] == 'ok'
            if expected_reward == 'fractional':
                assert 0 < case['marin_reward'] < 1
            else:
                assert case['marin_reward'] == expected_reward
            assert all(case[k] is True for k in ('native_initial_private_paths_absent', 'native_initial_imports_passed', 'marin_initial_private_paths_absent', 'marin_initial_imports_passed', 'marin_postgrade_private_paths_absent', 'passed'))
            for key in ('native_license_transport', 'marin_license_transport_verified'):
                license_file = case[key]
                assert license_file['sha256'] == frozen['license_sha256']
                assert license_file['mode'] == '0o644'
                assert license_file.get('kind', license_file.get('after')) == 'ordinary_file'
            case_rows.append({'case': case['case'], 'native_reward': case['native_reward'], 'Marin_reward': case['marin_reward'], 'native_grade_details_identical': True, 'license_bytes_and_mode_preserved': True})
        results.append({'pr': pr, 'pairs_passed': len(case_rows), 'cases': case_rows, 'profile_task_id': frozen['transport_profile_task_id']})
    return {'stage': 'exact_profile_native_Marin_parity_independently_reconciled', 'marin_revision': manifest['marin_revision'], 'profiles': len(results), 'pairs_passed': sum(x['pairs_passed'] for x in results), 'native_and_Marin_grade_executions': 2 * sum(x['pairs_passed'] for x in results), 'records': results, 'model_calls': 0, 'new_task_admissions': 0, 'Atlas_admissions': 0, 'limitations': ['Original symlink-collection failures remain separate historical results.', 'Validation covers these exact Docker builds and license-file transport TaskSpecs, not arbitrary symlinks or generic converter compatibility.', 'Functional private-path absence checks are not the deferred end-to-end integrity diagnostic.', 'Native correctness admissions and blind solver attempts are separate gates.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.summary.read_text()), args.inputs)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'limitations')}))
