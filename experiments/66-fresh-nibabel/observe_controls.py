"""Observe only the original frozen native control handle; no submission."""
import argparse,json
from datetime import datetime,UTC
from pathlib import Path
from biotasks.validation import bridge,preservation
from biotasks.validation.controller import verify_plan
from biotasks.validation.files import require,sha

args=argparse.ArgumentParser();args.add_argument('--logs',action='store_true');options=args.parse_args()
root=Path(__file__).resolve().parent
work=root/'inputs-private/run-001/nibabel-handoff/validation'
plan=verify_plan(work);group=plan['tasks'][0]
receipt=work/'runs'/group['id']/'submission.json'
require(receipt.is_file(),'No original submission receipt; do not create another job')
require(json.loads(receipt.read_text())['job_id']=='/exedev/'+group['run_id'],'Original handle differs')
profile=bridge.call(plan['backend'],{'action':'fingerprint'},root/'inputs-private/observer-profile.log')
require(profile==plan['client_profile'],'Observer SDK changed')
require(sha(Path(plan['backend']['config']))==plan['backend_config_sha256'],'Observer config changed')
result=bridge.call(plan['backend'],{'action':'logs' if options.logs else 'observe','group':group},root/'inputs-private/observer-status.log')
value=dict(observed_utc=datetime.now(UTC).isoformat(),original_job=result,read_only=True,new_model_calls=0,validation_plan_identity=plan['plan_identity'])
raw=json.dumps(value).encode();require(len(raw)<=512*1024,'Observation bound exceeded');preservation.inspect(raw,'original-control-observation.json')
stamp=datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ');target=root/('inputs-private' if options.logs else '.')/(('control-logs-' if options.logs else 'control-observation-')+stamp+'.json');target.write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(dict(path=str(target),rows=len(result.get('logs',[])),read_only=True,new_model_calls=0) if options.logs else value,indent=2))
