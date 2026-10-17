"""Bind recovered correctness outcomes to the exact original native task assets."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_skbio_pr_controls import retained_hashes
from repo2rlenv.emitter.bundle import inspect_bundle

EXPECTED = {'baseline': 0, 'native_reference': 1,
            'alternative_masked_division': 1, 'e_step_only': None,
            'wrong_uniform_responsibilities': 0,
            'fixed_underflow_with_grouping_regression': 0}


def reconcile(task, recovered, evidence):
    identity = inspect_bundle(task)
    assert identity['integrity_passed'], 'Original task identity mismatch'
    independent = recovered/'native/native/independent'
    manifest = json.loads((independent/'bundles/manifest.json').read_text())
    assert manifest['source_bundle_hash'] == identity['bundle_hash']
    retained = retained_hashes(task)
    assert manifest['unchanged_assets'] == retained
    contract = json.loads((task/'tests/contract.json').read_text())
    expected_tests = set(contract['expected_passes'])
    assert len(expected_tests) == 60
    summary = json.loads((independent/'summary.json').read_text())
    assert len(summary['records']) == len(EXPECTED)
    assert {r['case'] for r in summary['records']} == set(EXPECTED)
    rows = []
    for record in summary['records']:
        name = record['case']
        bundle = independent/'bundles'/name
        assert retained_hashes(bundle) == retained, 'Non-submission assets changed'
        assert record['completed'] and record['returncode'] == 0
        assert record['exception_type'] is None and record['passed']
        if EXPECTED[name] is not None:
            assert record['reward'] == EXPECTED[name]
        reports = list((independent/'jobs'/name).glob('*/verifier/result.json'))
        assert len(reports) == 1
        report = json.loads(reports[0].read_text())
        assert set(report['statuses']) == expected_tests
        passed = sum(value == 'passed' for value in report['statuses'].values())
        assert record['reward'] == int(passed == len(expected_tests))
        # Public small evidence must match recovered native reports exactly.
        assert (evidence/'verifier'/name/'result.json').read_bytes() == reports[0].read_bytes()
        rows.append({'case': name, 'reward': record['reward'], 'passed_tests': passed,
                     'total_tests': len(expected_tests),
                     'non_submission_asset_hashes_match': len(retained),
                     'solution_script_sha256': hashlib.sha256((bundle/'solution/solve.sh').read_bytes()).hexdigest()})
    assert json.loads((evidence/'cleanup-verification.json').read_text())['result'] == 'sandbox_absent'
    return {'stage':'recovered_native_controls_asset_reconciliation',
            'status':'correctness_controls_verified_acceptance_pending',
            'task':task.name, 'bundle_hash':identity['bundle_hash'],
            'native_integrity_passed':True, 'cases':rows,
            'reward_contract':'binary_all_expected_tests_pass',
            'competency':'Numerical underflow repair in ANCOM-BC expectation-maximization while preserving the scientific-library regression suite.',
            'scientific_reference':'Upstream R-reference log-fold changes and p-values; R itself was not rerun independently.',
            'coverage_limit':'E-step-only implementation passes the entire native suite; full intended numerical branch coverage is not established.',
            'lineage':'Same scikit-bio PR2633 as previous runtime/history variants, not a distinct independent problem.',
            'remaining_acceptance_gates':['Fresh learner/verifier runtime checks for the exact solver profile','Record all solver-profile interventions and repeat native reference checks'],
            'solver_attempts':0, 'new_model_calls':0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('task','recovered','evidence','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = reconcile(args.task, args.recovered, args.evidence)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'cases': len(result['cases']),
                      'bundle_hash': result['bundle_hash']}))
