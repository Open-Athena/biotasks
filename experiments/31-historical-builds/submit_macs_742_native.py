"""One bounded existing-reserved-worker probe. No model or repository credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, JobName, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from rigging.secrets import SecretBehavior
from rigging.timing import Duration

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['preflight', 'submit', 'observe'])
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--run-id', choices=['biotasks31-macs-742-native-001'], required=True)
args = parser.parse_args()
NAME = args.run_id
private = ROOT / 'run-private' / NAME
private.mkdir(mode=0o700, parents=True, exist_ok=True)
job_id = JobName.from_string('/exedev/' + NAME)
with connect_controller(config_file=args.config) as endpoint:
    with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
        if args.action == 'observe':
            job = client.job(job_id)
            status = job.status()
            logs = job.logs(max_lines=100, tail=True)
            payload = {'job_id':str(job_id),'state':str(status.state),'logs':[e.data for e in logs]}
            (private / 'observation.json').write_text(json.dumps(payload,indent=2)+'\n')
            for entry in logs:
                if entry.data.startswith('BIOTASKS31_NATIVE='):
                    result=json.loads(entry.data.split('=',1)[1]);(ROOT/('macs-742-native-result-'+NAME.rsplit('-',1)[1]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(payload))
        else:
            assert not client.list_jobs(prefix=str(job_id),limit=2), 'Handle exists; observe it, never resubmit'
            from iris.resources.state import is_job_finished
            assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks31-',limit=10)), 'Existing active probe: observe it'
            workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            target_worker=json.loads((ROOT/'run-private/biotasks31-macs-742-image-001/submission.json').read_text())['worker_id']
            eligible=[w for w in workers if w.worker_id==target_worker and w.healthy and 'v4-reserved' in w.scale_group and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            chosen=None
            for w in sorted(eligible,key=lambda x:(len(x.running_job_ids),x.worker_id)):
                allocations=[client.describe_task(JobName.from_string(t)).resources for t in w.running_job_ids]
                if w.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocations)>=4000 and w.metadata.memory_bytes-sum(r.memory_bytes for r in allocations)>=16*1024**3 and w.metadata.disk_bytes-sum(r.disk_bytes for r in allocations)>=16*1024**3:
                    chosen=w;break
            assert chosen is not None, 'No healthy existing reserved worker with headroom'
            source_pins=json.loads((ROOT/'macs-native-source-pins.json').read_text())
            names=['macs_native_742.py','macs-native-742-manifest.json','macs-native-source-pins.json','docker-tool.json',*source_pins]
            names += ['inputs-private/macs-native-742/'+name for name in json.loads((ROOT/'macs-native-742-manifest.json').read_text())['files']]
            files={name:(ROOT/name).read_bytes() for name in names}
            for name,digest in source_pins.items():assert hashlib.sha256(files[name]).hexdigest()==digest
            prior=json.loads((ROOT/'campaign-accounting.json').read_text())
            assert prior['all_terminal'] and prior['allocated_cpu_hours']+7<=16
            evidence={'job_id':str(job_id),'worker_id':chosen.worker_id,'worker_base':chosen.metadata.provenance.base_commit,
                      'new_capacity':False,'cpu':4,'memory_gib':16,'disk_gib':16,'timeout_seconds':6300,
                      'max_allocated_cpu_hours':7,'campaign_ceiling_cpu_hours':16,'prior_cpu_hours':prior['allocated_cpu_hours'],'model_calls':0,'attempts_allowed':1,
                      'payload_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()},
                      'checkpoint':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
            if args.action=='preflight':
                (private/'preflight.json').write_text(json.dumps(evidence,indent=2)+'\n')
                print(json.dumps(evidence));raise SystemExit(0)
            previous=json.loads((private/'preflight.json').read_text())
            assert previous['payload_sha256']==evidence['payload_sha256']
            target=private/'submission.json';assert not target.exists()
            evidence['state']='submission_pending';target.write_text(json.dumps(evidence,indent=2)+'\n')
            job=client.submit(name=NAME,
                entrypoint=Entrypoint(command=['bash','-c','exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/macs_native_742.py"'],workdir_files=files),
                resources=ResourceSpec(cpu=4,memory='16GB',disk='16GB'),
                environment=EnvironmentSpec(setup_scripts=[],env_vars={'PYTHONDONTWRITEBYTECODE':'1','BIOTASKS_RUN_ID':NAME},secret_behavior=SecretBehavior.ISOLATE),
                constraints=[Constraint.create(key='tpu-name',op=ConstraintOp.EQ,value=chosen.metadata.tpu_name),Constraint.create(key='tpu-worker-id',op=ConstraintOp.EQ,value=int(chosen.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180),timeout=Duration.from_seconds(6300),
                max_retries_failure=0,max_retries_preemption=0,priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id)==str(job_id)
            evidence['state']='submitted';target.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence))
