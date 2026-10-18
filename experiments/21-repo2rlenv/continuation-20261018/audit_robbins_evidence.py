"""Check archived native grades and independently reconstruct retained controls.

Only reads/copies captured files. No target package imports, Docker or model calls.
"""
import argparse
import collections
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def inventory(root):
    result = {}
    for file in sorted(root.rglob('*')):
        if file.is_symlink():
            raise ValueError('Unexpected linked task file')
        if file.is_file():
            with file.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            result[file.relative_to(root).as_posix()] = {'sha256': digest, 'mode': oct(file.stat().st_mode & 0o777)}
    return result


def audit(root):
    summary = json.loads((root / 'summary.json').read_text())
    manifest = json.loads((root / 'control-manifest.json').read_text())
    storage = json.loads((root / 'canonical-task-storage.json').read_text())
    native = root / storage['complete_native_task']
    assert storage['complete_native_task'] == manifest['native_task_relative_path']
    assert inventory(native) == manifest['native_assets']
    contract = json.loads((native / 'tests/contract.json').read_text())
    expected_names = set(contract['expected_passes'])
    assert contract['submitted_files'] == ['skbio/diversity/alpha/_base.py']
    cases = {row['case']: row for row in summary['records']}
    expected_cases = {row['case'] for row in manifest['cases']}
    assert len(cases) == len(summary['records']) and set(cases) == expected_cases
    assert set(storage['restored_control_hashes_and_permissions_verified']) == expected_cases
    assert summary['all_controls_executed_and_parsed'] and not summary['all_controls_passed']
    rows = []
    for name, row in cases.items():
        assert row['completed'] and row['executed_and_parsed'] and row['exception_type'] is None
        assert row['returncode'] == 0
        grades = list((root / 'jobs' / name).glob('**/verifier/result.json'))
        rewards = list((root / 'jobs' / name).glob('**/verifier/reward.txt'))
        assert len(grades) == len(rewards) == 1
        grade = json.loads(grades[0].read_text())
        assert grade == row['native_result']
        assert set(grade['statuses']) == expected_names
        assert float(rewards[0].read_text()) == row['reward']
        assert grade['passed'] == (row['reward'] == 1)
        rows.append({'case': name, 'native_reward': row['reward'], 'expected_control_reward': row['expected_reward'], 'native_status_counts': dict(collections.Counter(grade['statuses'].values())), 'actual_archived_grade_and_reward_match_summary': True})
    assert cases['baseline']['reward'] == cases['incorrect_zero']['reward'] == 0
    assert all(cases[name]['reward'] == 1 for name in ['native_reference', 'alternative', 'alternative_repeat', 'incorrect_constant_example'])
    restored_cases = []
    for name in ['alternative', 'incorrect_constant_example']:
        with tempfile.TemporaryDirectory(prefix='independent-control-restore-') as temporary:
            target = Path(temporary) / 'task'
            shutil.copytree(native, target)
            assert set(storage['profile_changed_assets']) <= {'task.toml'}
            assert set(storage['profile_deleted_assets']) <= {'environment/docker-compose.yaml'}
            for relative in storage['profile_deleted_assets']:
                (target / relative).unlink()
            for relative in storage['profile_changed_assets']:
                shutil.copy2(root / 'profile-delta' / relative, target / relative)
            solve = root / storage['control_solution_paths'][name]
            shutil.copy2(solve, target / 'solution/solve.sh')
            expected = dict(manifest['case_unchanged_assets'])
            expected['solution/solve.sh'] = {'sha256': hashlib.sha256(solve.read_bytes()).hexdigest(), 'mode': oct(solve.stat().st_mode & 0o777)}
            assert inventory(target) == expected
            if name == 'incorrect_constant_example':
                assert 'return np.float64(2 / 7)' in solve.read_text()
        restored_cases.append(name)
    return {'stage': 'native_task_rejected_insufficient_grader_coverage', 'candidate_id': summary['candidate_id'], 'native_expected_test_count': len(expected_names), 'controls_executed': len(rows), 'records': rows, 'native_task_all_asset_hashes_and_modes_verified': True, 'independent_control_reconstructions': restored_cases, 'constant_answer_native_reward': cases['incorrect_constant_example']['reward'], 'counterexample': {'counts': [1, 1], 'documented_F1_over_N': 1.0, 'constant_answer': 2 / 7}, 'decision': 'Reject original native task; constant nonempty answer passes native reward while violating the general public estimator contract.', 'new_independent_admissions': 0, 'new_solver_attempts': 0, 'model_calls': 0, 'deferred_end_to_end_integrity_diagnostic_executed': False, 'limits': ['This is an ordinary library implementation control with unchanged native tests/grader, not a report-tampering diagnostic.', 'Earlier capture failures remain separate; only this recovered run supplies measured native rewards.', 'No additional authoring calls remain for this candidate.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'limits')}))
