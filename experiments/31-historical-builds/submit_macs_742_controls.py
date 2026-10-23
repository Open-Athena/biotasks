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
parser.add_argument('--run-id', choices=['biotasks31-macs-742-controls-001'], required=True)
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
                if entry.data.startswith('BIOTASKS31_CONTROLS='):
                    result=json.loads(entry.data.split('=',1)[1]);(ROOT/('macs-742-controls-result-'+NAME.rsplit('-',1)[1]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(payload))
        else:
            assert not client.list_jobs(prefix=str(job_id),limit=2), 'Handle exists; observe it, never resubmit'
            from iris.resources.state import is_job_finished
            assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks31-macs-742-controls-',limit=10)), 'Existing active probe: observe it'
            prior=json.loads((ROOT/'campaign-accounting.json').read_text())
            assert prior['all_terminal'] and prior['allocated_cpu_hours']+4+1/6<=16
            assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks31-',limit=100)), 'Another #31 job active'
            manifest=json.loads((ROOT/'macs-native-742-manifest.json').read_text())
            inputs=json.loads((ROOT/'macs-742-control-inputs.json').read_text())
            exported=json.loads((ROOT/'macs-742-export-manifest.json').read_text())
            assert manifest['image_id']==exported['image_id'] and manifest['image_tag']==exported['image_tag']
            assert inputs['export_manifest_sha256']==hashlib.sha256((ROOT/'macs-742-export-manifest.json').read_bytes()).hexdigest()
            assert inputs['control_plan_sha256']==hashlib.sha256((ROOT/'macs-742-control-plan.json').read_bytes()).hexdigest()
            archive=ROOT/'inputs-private/macs-742-export/original-tasks.tar.gz'
            assert archive.stat().st_size==inputs['archive_bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==inputs['archive_sha256']
            native=json.loads((ROOT/'macs-742-native-readback-001.json').read_text())
            assert native['record_verified'] and native['owned_containers_absent'] and native['retained_image']==manifest['image_tag']
            assert [x['status'] for x in native['arms']]==['failed','verified']
            target_worker=json.loads((ROOT/'run-private/biotasks31-macs-742-image-001/submission.json').read_text())['worker_id']
            assert target_worker==manifest['image_worker_id']
            workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible=[w for w in workers if w.worker_id==target_worker and w.healthy and 'v4-reserved' in w.scale_group and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            chosen=None
            for w in sorted(eligible,key=lambda x:(len(x.running_job_ids),x.worker_id)):
                allocations=[client.describe_task(JobName.from_string(t)).resources for t in w.running_job_ids]
                if w.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocations)>=4000 and w.metadata.memory_bytes-sum(r.memory_bytes for r in allocations)>=16*1024**3 and w.metadata.disk_bytes-sum(r.disk_bytes for r in allocations)>=16*1024**3:
                    chosen=w;break
            assert chosen is not None, 'No healthy existing reserved worker with headroom'
            files={name:(ROOT/name).read_bytes() for name in ['macs_742_control_supervisor.py','cleanup_owned.py','harbor_docker.py','setup_controller.sh','run_existing_controls.py']}
            files['control-plan.json']=(ROOT/'macs-742-control-plan.json').read_bytes()
            files.update({'pins.json':(ROOT/'control-pins.json').read_bytes(),
                          'reconstruction-result.json':(json.dumps({'retained_image':manifest['image_tag'],'image_id':manifest['image_id']})+'\n').encode(),
                          'original-tasks.tar.gz':(ROOT/'inputs-private/macs-742-export/original-tasks.tar.gz').read_bytes()})
            evidence={'job_id':str(job_id),'worker_id':chosen.worker_id,'worker_base':chosen.metadata.provenance.base_commit,
                      'new_capacity':False,'cpu':4,'memory_gib':16,'disk_gib':16,'timeout_seconds':3600,
                      'max_allocated_cpu_hours':4,'model_calls':0,'attempts_allowed':1,
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
                entrypoint=Entrypoint(command=['bash','-c','exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/macs_742_control_supervisor.py"'],workdir_files=files),
                resources=ResourceSpec(cpu=4,memory='16GB',disk='16GB'),
                environment=EnvironmentSpec(setup_scripts=[],env_vars={'PYTHONDONTWRITEBYTECODE':'1','BIOTASKS_RUN_ID':NAME},secret_behavior=SecretBehavior.ISOLATE),
                constraints=[Constraint.create(key='tpu-name',op=ConstraintOp.EQ,value=chosen.metadata.tpu_name),Constraint.create(key='tpu-worker-id',op=ConstraintOp.EQ,value=int(chosen.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180),timeout=Duration.from_seconds(3600),
                max_retries_failure=0,max_retries_preemption=0,priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id)==str(job_id)
            evidence['state']='submitted';target.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence))
