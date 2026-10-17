import ast,hashlib,json,sys,tomllib
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Review the native observed_features bundle and preserved control manifest')
parser.add_argument('--task',type=Path,required=True)
parser.add_argument('--control-manifest',type=Path,required=True)
args=parser.parse_args()
exp=Path(__file__).resolve().parent;task=args.task
sys.path.insert(0,str(exp));from prepare_flow_independent_controls import retained_hashes
from repo2rlenv.emitter.bundle import inspect_bundle
identity=inspect_bundle(task);assert identity['integrity_passed']
manifest=args.control_manifest
controls=json.loads(manifest.read_text());assert controls['source_bundle_hash']==identity['bundle_hash'];assert controls['unchanged_asset_hashes']==retained_hashes(task)
records=json.loads((exp/'evidence/skbio-flow-independent-01/summary.json').read_text())['records'];assert len(records)==3 and all(x['passed'] and x['completed'] and x['exception_type'] is None for x in records)
native=json.loads((exp/'evidence/skbio-flow-controls-01/summary.json').read_text())['records'];native=next(x for x in native if x['candidate_id']=='c80f6a9306c83c7db638');assert native['native_controls_passed'];assert {x['agent']:x['reward'] for x in native['trials']}=={'nop':0,'oracle':1}
config=tomllib.loads((task/'task.toml').read_text());assert config['verifier']['environment_mode']=='separate'
contract=json.loads((task/'tests/contract.json').read_text());assert len(contract['expected_passes'])==34
learner=task/'environment/source';source=(learner/'skbio/diversity/alpha/_base.py').read_text();function=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='observed_features');assert isinstance(function.body[-1],ast.Expr) and isinstance(function.body[-1].value,ast.Constant) and function.body[-1].value.value is Ellipsis
report={'stage':'independent_bundle_and_contract_review','status':'acceptance_pending_runtime_boundary_checks','bundle_hash':identity['bundle_hash'],'native_integrity_passed':True,'asset_count':sum(1 for x in task.rglob('*') if x.is_file()),'instruction_sha256':hashlib.sha256((task/'instruction.md').read_bytes()).hexdigest(),'diagnostic_controls_same_non_submission_assets':True,'native_rewards':{'nop':0,'oracle':1},'independent_rewards':{x['case']:x['reward'] for x in records},'expected_test_count':34,'learner_target_is_stub':True,'verifier_declared_separate':True,'scientific_contract':'Return the same integer feature richness as existing sobs for valid count vectors; preserve other metrics.','competency':'Small alias reconstruction and library API compatibility; does not require independent biological inference.','limitations':['Raw instruction has literal n separators but substantive requirements remain readable; no rewriting performed.','Native test controls and static separation do not establish fresh solver/provider boundary checks.','No blind solver attempt or Marin conversion for this task.'],'next':'Validate fresh learner/verifier runtime and submission capture before final acceptance and one blind GLM attempt.'}
out=exp/'evidence/observed-features-acceptance-review';out.mkdir(exist_ok=True);(out/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
