"""Read-only bounded progress inspection of the single submitted controller."""
import argparse
import json
from pathlib import Path
from iris.cli.connect import connect_controller,rpc_client
from iris.rpc import controller_pb2

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);args=p.parse_args()
inner=r'''import json
from pathlib import Path
p=Path('/work/evidence/controls/controls.json')
if p.exists():
 rows=json.loads(p.read_text())
 print(json.dumps({'controls':[{'task':r['task'],'agent':r['agent'],'state':r['state'],'exit_code':r.get('exit_code'),'started':r.get('started'),'finished':r.get('finished'),'trial_results':r.get('trial_results',[]),'reward_files':r.get('reward_files',{})} for r in rows]}))
else:print('Controls not started; controller setup in progress')
'''
outer='''from pathlib import Path
import subprocess,os
p=Path(os.environ['IRIS_WORKDIR'])/'control-tools/docker'
if p.exists():
 r=subprocess.run([str(p),'exec','biotasks29-matchms-controls-001-controller','python','-c',%r],capture_output=True,text=True,timeout=20)
 print(r.stdout);print(r.stderr)
else:print('Controller CLI not available')
''' % inner
with connect_controller(config_file=args.config) as endpoint:
 with rpc_client(endpoint.url,endpoint.credentials,timeout_ms=45000) as client:
  result=client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(task_id='/exedev/biotasks29-matchms-controls-001/0',command=['bash','-c','exec "$IRIS_PYTHON" -c "$1"','_',outer],timeout_seconds=30))
  data={'stdout':result.stdout,'stderr':result.stderr,'exit_code':result.exit_code,'error':result.error}
  target=ROOT/'run-private/biotasks29-matchms-controls-001/live-inspection.json'
  target.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
