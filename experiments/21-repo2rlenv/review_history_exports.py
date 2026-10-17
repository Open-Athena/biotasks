"""Review native history exports and prepare correctness controls, without execution."""
import argparse
import ast
import hashlib
import json
import tomllib
from pathlib import Path

from repo2rlenv.emitter.bundle import inspect_bundle
from prepare_skbio_pr_controls import prepare


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def review(task, evidence, controls):
    identity = inspect_bundle(task)
    assert identity['integrity_passed']
    config = tomllib.loads((task/'task.toml').read_text())
    contract = json.loads((task/'tests/contract.json').read_text())
    assert config['verifier']['environment_mode'] == 'separate'
    assert contract['submitted_files'] == ['skbio/stats/composition/_ancombc.py']
    expected = set(contract['expected_passes'])
    assert len(expected) == 60
    native = json.loads((evidence/'summary.json').read_text())
    contrast = {}
    for case in ('healthy', 'defective'):
        statuses = json.loads((evidence/f'{case}-results.json').read_text())['statuses']
        assert set(statuses) == expected
        contrast[case] = statuses
    assert all(x == 'passed' for x in contrast['healthy'].values())
    failed = [x for x, value in contrast['defective'].items() if value != 'passed']
    assert len(failed) == 1 and failed[0].endswith('CoreTests::test_estimate_bias_em_underflow')
    for case, reward in [('nop', 0), ('oracle', 1)]:
        record = json.loads((evidence/f'{case}-trial.json').read_text())
        assert record['bundle_hash'] == identity['bundle_hash']
        assert record['reward'] == reward and record['exception_type'] is None
    tests = task/'tests/source'/contract['test_paths'][0]
    tree = ast.parse(tests.read_text())
    regression = [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef) and x.name == 'test_estimate_bias_em_underflow']
    assert len(regression) == 1
    instruction = (task/'instruction.md').read_text()
    assert 'Quantiles' in instruction and 'underflow' in instruction
    assert '_ancombc.py' in instruction and 'offline' in instruction
    grader = (task/'tests/grade.py').read_text()
    assert 'reward.write_text("1\\n" if passed else "0\\n")' in grader
    records = prepare(task, controls, partial=True)
    # These history tasks use binary all-tests-pass reward, unlike PR-runtime's fractional reward.
    manifest_path = controls/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for row in manifest['cases']:
        if row['case'] == 'fixed_underflow_with_grouping_regression':
            row['expected_reward'] = 0
    manifest['reward_contract'] = 'binary_all_expected_tests_pass'
    manifest['source_bundle_hash'] = identity['bundle_hash']
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    return {'stage': 'independent_static_review_controls_prepared',
            'status': 'acceptance_pending_independent_runtime_controls',
            'task': task.name, 'bundle_hash': identity['bundle_hash'],
            'native_integrity_passed': True, 'expected_tests': 60,
            'healthy_passes': 60, 'defective_passes': 59,
            'regression_test_ast_sha256': hashlib.sha256(ast.dump(regression[0], include_attributes=False).encode()).hexdigest(),
            'learner_source_sha256': digest(task/'environment/source/skbio/stats/composition/_ancombc.py'),
            'reference_source_sha256': digest(task/'solution/reference/skbio/stats/composition/_ancombc.py'),
            'grader_sha256': digest(task/'tests/grade.py'),
            'controls_prepared': [{k:v for k,v in x.items() if k!='bundle'} for x in manifest['cases']],
            'unchanged_asset_count': len(manifest['unchanged_assets']),
            'native_rewards': {'nop':0, 'oracle':1}, 'blind_attempts':0,
            'scientific_contract': 'Avoid EM underflow NaNs and match the upstream R-reference log-fold changes and p-values while preserving other behavior.',
            'limitations': ['Same PR2633 lineage as existing PR-runtime task.',
                           'R-reference values are upstream reported, not independently rerun in R here.',
                           'Native instruction formatting is compressed but substantive requirements are readable.',
                           'Prepared controls have not been executed on these exported bundles; runtime separation is not established by static review.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('task','evidence','controls','report'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = review(args.task, args.evidence, args.controls)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
