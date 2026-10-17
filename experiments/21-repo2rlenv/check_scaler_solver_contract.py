import runpy,sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
runpy.run_path(str(ROOT/'check_pr_provider_preflight.py'),run_name='__main__')
runpy.run_path(str(ROOT/'check_pr_blind_solver.py'),run_name='__main__')
from run_pr_blind_solver import check_controls
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);base={'exception_info':None,'verifier_result':{'rewards':{'reward':-1}},'task_checksum':'fixture'};ref={'status':'passed','model_calls':0,'cases':[{'agent':'oracle','result':{'exception_info':None,'verifier_result':{'rewards':{'reward':1}},'task_checksum':'fixture'}}]}
 (p/'base.json').write_text(json.dumps(base));(p/'ref.json').write_text(json.dumps(ref))
 assert check_controls(p/'base.json',p/'ref.json',-1)=='fixture'
 try:check_controls(p/'base.json',p/'ref.json',0)
 except AssertionError:pass
 else:raise AssertionError('Wrong baseline contract accepted')
print('PASS: native negative baseline accepted only under explicit -1 contract')
