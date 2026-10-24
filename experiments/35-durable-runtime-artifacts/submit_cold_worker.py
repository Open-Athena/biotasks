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
parser.add_argument('--run-id', choices=['biotasks35-cobrapy-1482-inline-001'], required=True)
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
            try:
                logs = job.logs(max_lines=20, tail=True)
            except Exception:
                logs = []
            payload = {'job_id':str(job_id),'state':str(status.state),'logs':[e.data for e in logs]}
            (private / 'observation.json').write_text(json.dumps(payload,indent=2)+'\n')
            for entry in logs:
                if entry.data.startswith('BIOTASKS34_CONFIRMATION='):
                    result=json.loads(entry.data.split('=',1)[1]);(ROOT/'cold-observed-result.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(payload))
        else:
            assert not client.list_jobs(prefix=str(job_id),limit=2), 'Handle exists; observe it, never resubmit'
            from iris.resources.state import is_job_finished
            assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks35-',limit=10)), 'Existing active probe: observe it'
            workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible=[w for w in workers if w.healthy and 'v4-reserved' in w.scale_group and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            excluded=json.loads((ROOT/'inputs-private/original-workers.json').read_text())
            eligible=[w for w in eligible if w.worker_id not in excluded['excluded_worker_ids'] and w.metadata.tpu_name not in excluded['excluded_tpu_names'] and w.metadata.provenance.base_commit.startswith('c7c14a252d')]
            chosen=None
            for w in sorted(eligible,key=lambda x:(len(x.running_job_ids),x.worker_id)):
                allocations=[client.describe_task(JobName.from_string(t)).resources for t in w.running_job_ids]
                if w.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocations)>=4000 and w.metadata.memory_bytes-sum(r.memory_bytes for r in allocations)>=16*1024**3 and w.metadata.disk_bytes-sum(r.disk_bytes for r in allocations)>=16*1024**3:
                    chosen=w;break
            assert chosen is not None, 'No healthy existing reserved worker with headroom'
            manifest=json.loads((ROOT/'cold-payload-manifest.json').read_text())
            subprocess.run(['git','ls-files','--error-unmatch',str(ROOT/'cold-payload-manifest.json')],cwd=ROOT,check=True,capture_output=True)
            subprocess.run(['git','diff','--exit-code','HEAD','--',str(ROOT/'cold-payload-manifest.json')],cwd=ROOT,check=True,capture_output=True)
            payload=ROOT/'inputs-private/cold-payload'
            files={p.name:p.read_bytes() for p in payload.iterdir() if p.is_file()}
            assert set(files)==set(manifest['sha256'])|{'cold-payload.json'}
            assert json.loads(files['cold-payload.json'])==manifest
            assert all(hashlib.sha256(files[name]).hexdigest()==value for name,value in manifest['sha256'].items())
            budget=json.loads((ROOT/'cold-cpu-reservation.json').read_text())
            assert budget['run_id']==NAME and budget['maximum_cpu_hours']==4
            assert budget['reservation_state']=='booked in epic 33 budget before submission'
            assert budget['prior_child_allocated_cpu_hours']+4+budget['cleanup_allowance_cpu_hours']<=8
            evidence={'job_id':str(job_id),'worker_id':chosen.worker_id,'worker_base':chosen.metadata.provenance.base_commit,
                      'different_worker_constraint_verified':True,'new_capacity':False,'cpu':4,'memory_gib':16,'disk_gib':16,'timeout_seconds':3600,
                      'max_allocated_cpu_hours':4,'campaign_ceiling_cpu_hours':8,'epic_ceiling_cpu_hours':32,'model_calls':0,'attempts_allowed':1,
                      'payload_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()},
                      'checkpoint':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
            if args.action=='preflight':
                (private/'preflight.json').write_text(json.dumps(evidence,indent=2)+'\n')
                print(json.dumps(evidence));raise SystemExit(0)
            live_budget=json.loads((ROOT.parents[2]/'33/experiments/33-unattended-validation/budget.json').read_text())
            assert live_budget['additional_allocated_cpu_hours']+live_budget['outstanding_cpu_hour_reservations']<=32
            assert any(e.get('run_id')==NAME and e['state']=='reserved before submission' for e in live_budget['events'])
            previous=json.loads((private/'preflight.json').read_text())
            assert previous['payload_sha256']==evidence['payload_sha256']
            target=private/'submission.json';assert not target.exists()
            evidence['state']='submission_pending';target.write_text(json.dumps(evidence,indent=2)+'\n')
            job=client.submit(name=NAME,
                entrypoint=Entrypoint(command=['bash','-c','exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/cold_worker_job.py"'],workdir_files=files),
                resources=ResourceSpec(cpu=4,memory='16GB',disk='16GB'),
                environment=EnvironmentSpec(setup_scripts=[],env_vars={'PYTHONDONTWRITEBYTECODE':'1','BIOTASKS_RUN_ID':NAME,'BIOTASKS_EXPECTED_WORKER':chosen.worker_id},secret_behavior=SecretBehavior.ISOLATE),
                constraints=[Constraint.create(key='tpu-name',op=ConstraintOp.EQ,value=chosen.metadata.tpu_name),Constraint.create(key='tpu-worker-id',op=ConstraintOp.EQ,value=int(chosen.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180),timeout=Duration.from_seconds(3600),
                max_retries_failure=0,max_retries_preemption=0,priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id)==str(job_id)
            evidence['state']='submitted';target.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence))
