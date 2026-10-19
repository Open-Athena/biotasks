"""Audit archived native controls without importing or executing target packages."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from audit_authored_blind_batch import binary_grade
from audit_authored_native_evidence import source_from_script
from audit_robbins_evidence import inventory

PROFILES = {
    'f4c2d9ca15940793cc88': ('michaelis_menten_fit', ('incorrect_constant_one', 'incorrect_observed_richness')),
    '2bc29fe20c34fbca2661': ('michaelis_menten_fit', ('incorrect_constant_one', 'incorrect_observed_richness')),
    'f39ded25ef48a6575366': ('tsallis', ('incorrect_zero', 'incorrect_ignore_order')),
}


def audit(root):
    summary = json.loads((root / 'summary.json').read_text())
    manifest = json.loads((root / 'control-manifest.json').read_text())
    storage = json.loads((root / 'canonical-task-storage.json').read_text())
    function, negatives = PROFILES[summary['candidate_id']]
    task = root / storage['complete_native_task']
    assert storage['complete_native_task'] == manifest['native_task_relative_path']
    assets = inventory(task)
    assert assets == manifest['native_assets']
    contract = json.loads((task / 'tests/contract.json').read_text())
    source_path = 'skbio/diversity/alpha/_base.py'
    test_path = 'skbio/diversity/alpha/tests/test_base.py'
    assert contract['submitted_files'] == [source_path]
    assert not (task / 'environment/source' / test_path).exists()
    assert (task / 'tests/source' / test_path).is_file()
    assert not (task / 'environment/source/solution/solve.sh').exists()
    assert set(storage['profile_changed_assets']) <= {'task.toml'}
    assert set(storage['profile_deleted_assets']) <= {'environment/docker-compose.yaml'}
    profile = dict(assets)
    for name in storage['profile_deleted_assets']:
        del profile[name]
    for name in storage['profile_changed_assets']:
        f = root / 'profile-delta' / name
        profile[name] = {'sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'mode': oct(f.stat().st_mode & 0o777)}
    assert profile == manifest['profile_assets']
    expected = {'baseline': 0, 'native_reference': 1, 'alternative': 1, 'alternative_repeat': 1, **dict.fromkeys(negatives, 0)}
    records = {r['case']: r for r in summary['records']}
    assert len(records) == len(summary['records']) == 6 and set(records) == set(expected)
    assert set(storage['restored_control_hashes_and_permissions_verified']) == set(expected)
    rows = []
    source = (task / 'environment/source' / source_path).read_text()
    for name, reward in expected.items():
        r = records[name]
        assert r['completed'] and r['executed_and_parsed'] and r['passed']
        assert r['exception_type'] is None and r['returncode'] == 0
        grades = list((root / 'jobs' / name).glob('**/verifier/result.json'))
        assert len(grades) == 1
        grade = json.loads(grades[0].read_text())
        assert grade == r['native_result'] and set(grade['statuses']) == set(contract['expected_passes'])
        result = binary_grade(grades[0].parent.parent, None, None)
        assert result['reward'] == reward == r['reward']
        solution = root / storage['control_solution_paths'][name]
        restored = dict(profile)
        restored['solution/solve.sh'] = {'sha256': hashlib.sha256(solution.read_bytes()).hexdigest(), 'mode': oct(solution.stat().st_mode & 0o777)}
        assert {k: v for k, v in restored.items() if k != 'solution/solve.sh'} == manifest['case_unchanged_assets']
        if name in ('alternative', 'alternative_repeat', *negatives):
            before, after = ast.parse(source), ast.parse(source_from_script(solution.read_text()))
            old = next(n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == function)
            new = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == function)
            assert ast.get_docstring(old) == ast.get_docstring(new)
            before.body.remove(old)
            after.body.remove(new)
            assert ast.dump(before) == ast.dump(after), 'Unexpected changes outside target function'
        rows.append({'case': name, **result})
    return {'stage': 'native_controls_audited_instruction_review_and_preservation_separate', 'candidate_id': summary['candidate_id'], 'function': function, 'controls': rows, 'native_assets_and_control_hashes_verified': True, 'only_selected_function_changed_by_alternatives_and_negatives': True, 'native_grader_and_instruction_unchanged': True, 'junit_native_reward_agreement': True, 'target_tests_absent_from_learner_source': True, 'independently_admitted': False, 'model_calls': 0, 'new_solver_attempts': 0, 'limitations': ['These controls exercise the native test contract; they do not prove every generated instruction claim.', 'Manual control preparation is validation assistance, not an autonomous acceptance pipeline.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'candidate': result['candidate_id'], 'rewards': [r['reward'] for r in result['controls']], 'admitted': False}))
