"""Review native QCP control evidence without claiming final task acceptance."""
import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from repo2rlenv.emitter.bundle import inspect_bundle
from prepare_skbio_pr_controls import retained_hashes

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--task', type=Path, required=True)
parser.add_argument('--controls', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
identity = inspect_bundle(args.task)
assert identity['integrity_passed']
manifest = json.loads((args.controls/'independent/bundles/manifest.json').read_text())
assert manifest['source_bundle_hash'] == identity['bundle_hash']
assert manifest['unchanged_assets'] == retained_hashes(args.task)
contract = json.loads((args.task/'tests/contract.json').read_text())
assert contract['submitted_files'] == ['Bio/PDB/qcprot.py']
assert len(contract['expected_passes']) == 9
config = tomllib.loads((args.task/'task.toml').read_text())
assert config['verifier']['environment_mode'] == 'separate'
assert all(config[s]['network_mode'] == 'no-network' for s in ('environment','agent','verifier'))
summary = json.loads((args.controls/'independent/summary.json').read_text())
expected = {'baseline':0, 'native_reference':1, 'alternative_svd':1,
            'wrong_translation':0, 'wrong_identity_rotation':0, 'wrong_zero_reported_rms':0}
assert {r['case']:r['reward'] for r in summary['records']} == expected
reports = []
for row in summary['records']:
    assert row['passed'] and row['completed'] and row['exception_type'] is None
    matches = list((args.controls/'independent/jobs'/row['case']).glob('*/verifier/result.json'))
    assert len(matches) == 1
    result = json.loads(matches[0].read_text())
    assert set(result['statuses']) == set(contract['expected_passes'])
    assert float((matches[0].parent/'reward.txt').read_text()) == row['reward']
    reports.append({'case':row['case'], 'reward':row['reward'],
                    'passed_tests':sum(v=='passed' for v in result['statuses'].values()),
                    'tests':len(result['statuses'])})
paths = ['instruction.md','task.toml','tests/contract.json',
         'tests/source/Tests/test_PDB_QCPSuperimposer.py','environment/Dockerfile','tests/Dockerfile']
record = {
    'stage':'independent_instruction_and_contract_review',
    'status':'acceptance_pending_runtime_and_tolerance_review',
    'source_bundle_hash':identity['bundle_hash'],
    'native_integrity_passed':True,
    'unchanged_non_solution_assets':len(manifest['unchanged_assets']),
    'controls':reports,
    'competency':'Numerical coordinate alignment repair in a structural biology library; includes synthetic coordinate arrays and a retained PDB fixture.',
    'instruction_verifier_agreement':{
        'submission':'Only Bio/PDB/qcprot.py is collected; unchanged tests run separately.',
        'collinear_regression':'Instruction reproduction matches the specific regression checked at 12 decimal places for transformed RMSD.',
        'nondegenerate_tolerance':'Instruction suggests agreement near 1e-15; native comparison tests use atol=1e-3 and three decimal places for ordinary SVD comparisons. The stricter instruction claim is not established by the reward.',
        'generalization':'Instruction requires arbitrary collinear rotations/translations; one new regression plus existing line tests does not establish universal coverage.'},
    'limitations':['Successful controls establish bounded correctness evidence, not general numerical guarantees.',
                   'Native instruction supplies a concrete reproduction and diagnosis; record this assistance when interpreting solver performance.',
                   'Fresh learner/verifier provider readiness remains unexecuted.',
                   'No final acceptance or blind solver result is claimed.'],
    'source_sha256':{name:hashlib.sha256((args.task/name).read_bytes()).hexdigest() for name in paths}}
args.output.mkdir(parents=True,exist_ok=True)
(args.output/'review.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':record['status'],'controls':reports}))
