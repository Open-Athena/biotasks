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
parser.add_argument('--run-id', choices=['biotasks29-scanpy-recorded-cleanup-001'], required=True)
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
            # Log transport failure must not hide authoritative job status.
            logs_error = None
            try:
                logs = job.logs(max_lines=100, tail=True)
            except Exception as error:
                logs = []
                logs_error = type(error).__name__
            payload = {'job_id':str(job_id),'state':str(status.state),'logs':[e.data for e in logs],'logs_error':logs_error}
            (private / 'observation.json').write_text(json.dumps(payload,indent=2)+'\n')
            for entry in logs:
                if entry.data.startswith('BIOTASKS29_CLEANUP='):
                    result=json.loads(entry.data.split('=',1)[1]);(ROOT/('scanpy-recorded-cleanup-result-'+NAME.rsplit('-',1)[1]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(payload))
        else:
            assert not client.list_jobs(prefix=str(job_id),limit=2), 'Handle exists; observe it, never resubmit'
            from iris.resources.state import is_job_finished
            assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks29-scanpy-recorded-cleanup-',limit=10)), 'Existing active probe: observe it'
            prior=json.loads((ROOT/'scanpy-control-results.json').read_text())
            assert prior['task_files_unchanged'] and prior['owned_control_resources_removed']
            terminal=json.loads((ROOT/'campaign-accounting.json').read_text())
            scanpy_extra=0 if 'biotasks29-scanpy-controls-001' in terminal['jobs'] else prior['allocated_cpu_hours_controls']
            assert terminal['allocated_cpu_hours']+scanpy_extra+8+1/6<=32
            assert is_job_finished(client.job(JobName.from_string('/exedev/biotasks29-scanpy-controls-001')).status().state)
            assert prior['archive_sha256']==json.loads((ROOT/'scanpy-controls-accounting.json').read_text())['output_archive']['sha256']
            target_worker=json.loads((ROOT/'scanpy-recorded-submission.json').read_text())['worker_id']
            workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible=[w for w in workers if w.worker_id==target_worker and w.healthy and 'v4-reserved' in w.scale_group and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            chosen=None
            for w in sorted(eligible,key=lambda x:(len(x.running_job_ids),x.worker_id)):
                allocations=[client.describe_task(JobName.from_string(t)).resources for t in w.running_job_ids]
                if w.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocations)>=2000 and w.metadata.memory_bytes-sum(r.memory_bytes for r in allocations)>=2*1024**3 and w.metadata.disk_bytes-sum(r.disk_bytes for r in allocations)>=2*1024**3:
                    chosen=w;break
            assert chosen is not None, 'No healthy existing reserved worker with headroom'
            files={name:(ROOT/name).read_bytes() for name in ['cleanup_scanpy_recorded.py','docker-tool.json']}
            image=json.loads((ROOT/'scanpy-recorded-result-001.json').read_text())
            files['image-binding.json']=(json.dumps({'tag':image['retained_image_tag'],'id':image['retained_image_id']})+'\n').encode()
            evidence={'job_id':str(job_id),'worker_id':chosen.worker_id,'worker_base':chosen.metadata.provenance.base_commit,
                      'new_capacity':False,'cpu':2,'memory_gib':2,'disk_gib':2,'timeout_seconds':300,
                      'max_allocated_cpu_hours':1/6,'model_calls':0,'attempts_allowed':1,
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
                entrypoint=Entrypoint(command=['bash','-c','exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/cleanup_scanpy_recorded.py"'],workdir_files=files),
                resources=ResourceSpec(cpu=2,memory='2GB',disk='2GB'),
                environment=EnvironmentSpec(setup_scripts=[],env_vars={'PYTHONDONTWRITEBYTECODE':'1','BIOTASKS_RUN_ID':NAME},secret_behavior=SecretBehavior.ISOLATE),
                constraints=[Constraint.create(key='tpu-name',op=ConstraintOp.EQ,value=chosen.metadata.tpu_name),Constraint.create(key='tpu-worker-id',op=ConstraintOp.EQ,value=int(chosen.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180),timeout=Duration.from_seconds(300),
                max_retries_failure=0,max_retries_preemption=0,priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id)==str(job_id)
            evidence['state']='submitted';target.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence))
