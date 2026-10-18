"""Reconcile actual archived binary grades and retained control assets.

No target package imports, builds, model calls or new grader executions.
"""

import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path

from audit_robbins_evidence import inventory


def entropy_table_call(function):
    calls = [n for n in ast.walk(function) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == 'compone' and n.func.attr == 'append']
    assert len(calls) == 1 and len(calls[0].args) == 1
    return calls[0]


def source_from_script(script):
    program = script.split("python3 - <<'PYCONTROL'\n", 1)[1].split('\nPYCONTROL', 1)[0]
    calls = [n for n in ast.walk(ast.parse(program)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'write_text']
    assert len(calls) == 1 and len(calls[0].args) == 1
    return ast.literal_eval(calls[0].args[0])


def audit(root):
    summary = json.loads((root / 'summary.json').read_text())
    manifest = json.loads((root / 'control-manifest.json').read_text())
    storage = json.loads((root / 'canonical-task-storage.json').read_text())
    assert summary['candidate_id'] in ('3ad7ba60ca7686b2007b', '53ec5f51639d4053971f')
    is_flow = summary['candidate_id'] == '3ad7ba60ca7686b2007b'
    native = root / storage['complete_native_task']
    assert storage['complete_native_task'] == manifest['native_task_relative_path']
    native_assets = inventory(native)
    assert native_assets == manifest['native_assets']
    contract = json.loads((native / 'tests/contract.json').read_text())
    expected_names = set(contract['expected_passes'])
    source_file = 'skbio/diversity/alpha/_base.py' if is_flow else 'Bio/SeqUtils/lcc.py'
    test_file = 'skbio/diversity/alpha/tests/test_base.py' if is_flow else 'Tests/test_SeqUtils.py'
    collected = ['skbio/diversity/alpha/_base.py'] if is_flow else ['Bio/SeqUtils/' + name for name in ['CheckSum.py', 'IsoelectricPoint.py', 'MeltingTemp.py', 'ProtParam.py', 'ProtParamData.py', '__init__.py', 'lcc.py']]
    assert sorted(contract['submitted_files']) == sorted(collected)
    assert not (native / 'environment/source' / test_file).exists()
    assert (native / 'tests/source' / test_file).is_file()
    assert not (native / 'environment/source/solution/solve.sh').exists()
    assert summary['all_controls_executed_and_parsed'] and summary['all_controls_passed']
    expected = {'baseline': 0, 'native_reference': 1, 'alternative': 1, 'alternative_repeat': 1, 'incorrect_zero': 0, 'incorrect_ignore_finite' if is_flow else 'incorrect_constant_example': 0}
    cases = {row['case']: row for row in summary['records']}
    assert len(cases) == len(summary['records']) == 6 and set(cases) == set(expected)
    assert set(storage['restored_control_hashes_and_permissions_verified']) == set(expected)
    assert set(storage['profile_changed_assets']) <= {'task.toml'}
    assert set(storage['profile_deleted_assets']) <= {'environment/docker-compose.yaml'}
    # Independently derive every restored file digest/mode from retained bytes.
    # The remote canonicalizer also exercised full physical reconstruction.
    profile_assets = dict(native_assets)
    for relative in storage['profile_deleted_assets']:
        del profile_assets[relative]
    for relative in storage['profile_changed_assets']:
        file = root / 'profile-delta' / relative
        profile_assets[relative] = {'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'mode': oct(file.stat().st_mode & 0o777)}
    assert profile_assets == manifest['profile_assets']
    rows = []
    for name, reward in expected.items():
        row = cases[name]
        assert row['completed'] and row['executed_and_parsed'] and row['passed']
        assert row['exception_type'] is None and row['returncode'] == 0
        grades = list((root / 'jobs' / name).glob('**/verifier/result.json'))
        rewards = list((root / 'jobs' / name).glob('**/verifier/reward.txt'))
        assert len(grades) == len(rewards) == 1
        grade = json.loads(grades[0].read_text())
        assert grade == row['native_result'] and set(grade['statuses']) == expected_names
        assert float(rewards[0].read_text()) == row['reward'] == reward
        assert grade['passed'] == (reward == 1)
        solution = root / storage['control_solution_paths'][name]
        restored = dict(profile_assets)
        restored['solution/solve.sh'] = {'sha256': hashlib.sha256(solution.read_bytes()).hexdigest(), 'mode': oct(solution.stat().st_mode & 0o777)}
        assert {k: v for k, v in restored.items() if k != 'solution/solve.sh'} == manifest['case_unchanged_assets']
        rows.append({'case': name, 'native_reward': reward, 'native_status_counts': dict(collections.Counter(grade['statuses'].values())), 'actual_archived_grade_and_reward_match_summary': True, 'restored_control_hashes_and_modes_verified': True})
    source = (native / 'environment/source' / source_file).read_text()
    baseline_tree = ast.parse(source)
    function_name = 'enspie' if is_flow else 'lcc_mult'
    baseline_function = next(n for n in baseline_tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
    if is_flow:
        assert len(baseline_function.body) == 2
        stub = baseline_function.body[-1]
        assert isinstance(stub, ast.Expr) and isinstance(stub.value, ast.Constant) and stub.value.value is Ellipsis
    baseline_documentation = ast.get_docstring(baseline_function)
    original_body = baseline_function.body
    negatives = [('incorrect_zero', '0.0'), ('incorrect_ignore_finite', 'inv_simpson(counts)')] if is_flow else [('incorrect_zero', '[0.0] * (len(seq) - wsize + 1)'), ('incorrect_constant_example', '[0.9528195311147832] * (len(seq) - wsize + 1)')]
    for name, expression in [('alternative', '1.0 / dominance(counts, finite=finite)'), ('alternative_repeat', '1.0 / dominance(counts, finite=finite)'), *negatives]:
        script = (root / storage['control_solution_paths'][name]).read_text()
        changed = ast.parse(source_from_script(script))
        function = next(n for n in changed.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
        assert ast.get_docstring(function) == baseline_documentation
        if not is_flow and name.startswith('alternative'):
            actual = entropy_table_call(function)
            assert ast.dump(actual.args[0]) == ast.dump(ast.parse('((i + 1) / wsize) * math.log2((i + 1) / wsize) / 2', mode='eval').body)
            original = ast.parse(source)
            original_function = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
            entropy_table_call(original_function).args = [ast.Constant(value='NORMALIZATION_SITE')]
            actual.args = [ast.Constant(value='NORMALIZATION_SITE')]
            assert ast.dump(changed) == ast.dump(original)
            continue
        assert len(function.body) == 2 and isinstance(function.body[-1], ast.Return)
        assert ast.dump(function.body[-1].value) == ast.dump(ast.parse(expression, mode='eval').body)
        function.body = []
        baseline_function.body = []
        assert ast.dump(changed) == ast.dump(baseline_tree)
        baseline_function.body = original_body
    scope = ['Alias/finite-argument forwarding is a small diversity-library wiring competency, not a biodiversity analysis workflow.', 'Native synthetic count-vector fixtures; no newly observed biological cohort.', 'Original generated literal n separators retained; readable contract not silently reformatted.'] if is_flow else ['Normalized local-composition entropy repair; a small biological-library algorithm task.', 'LCC examples use upstream synthetic DNA/protein strings; unrelated regressions also read the retained observed GenBank NC_005816 fixture.', 'Existing rolling behavior and unrelated source functions are preserved; this is not a new biological analysis workflow.']
    return {'stage': 'authored_native_controls_independently_audited_public_preservation_pending', 'candidate_id': summary['candidate_id'], 'recipe': summary['recipe'], 'native_expected_test_count': len(expected_names), 'controls_executed': 6, 'records': rows, 'native_task_all_asset_hashes_and_modes_verified': True, 'source_edits_independently_checked': True, 'hidden_native_target_tests_absent_from_learner': True, 'private_solution_outside_learner_build_context': True, 'native_grader_and_instruction_unchanged': True, 'decision': 'All declared binary correctness controls pass; eligible for bounded native admission after public preservation/readback and cleanup verification.', 'model_calls': 0, 'new_solver_attempts': 0, 'limits': [*scope, 'One candidate/task lineage; no broader quality or isolation guarantee.', 'Marin parity and blind GLM attempt remain pending.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'limits')}))
