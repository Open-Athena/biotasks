"""Fixed-handle Iris transport; no scientific outcome inferred from job state."""
import argparse
import dataclasses
import json
from pathlib import Path
import subprocess
import time

from common import sha,write

ROOT=Path(__file__).resolve().parent


def load(family_id,cleanup=False):
    plan=json.loads((ROOT/'runtime-plan.json').read_text())
    assert not plan['model_calls_enabled'] and not plan['new_capacity_allowed']
    family=next(f for f in plan['families'] if f['id']==family_id)
    assert family['mode']=='recorded_bootstrap_dependency' and family['run_id']
    base=ROOT/'private'/family_id;directory=base/'cleanup' if cleanup else base
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    payload=ROOT/family['cleanup_payload_directory' if cleanup else 'payload_directory']
    expected=family['cleanup_payload_sha256' if cleanup else 'payload_sha256']
    files={p.name:p.read_bytes() for p in payload.iterdir() if p.is_file()}
    assert set(files)==set(expected)
    assert all(sha(payload/name)==value for name,value in expected.items())
    if cleanup:
        primary=json.loads((base/'submission.json').read_text())
        family=dict(family,primary_run_id=family['run_id'],run_id=family['run_id']+'-cleanup',
            payload_sha256=expected,resources=dict(cpus=2,memory_gib=4,disk_gib=2,timeout_seconds=270),
            cleanup_target=primary)
    return family,directory,files


def choose_worker(client,config):
    from iris.rpc import controller_pb2
    from iris.cluster.types import JobName
    workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
    excluded=config['exclusions'];resources=config['resources']
    blocked_names={w.metadata.tpu_name for w in workers if w.worker_id in excluded['excluded_worker_ids']}
    eligible=[w for w in workers if w.healthy and 'v4-reserved' in w.scale_group and
        not w.metadata.provenance.dirty and w.metadata.provenance.base_commit.startswith('c7c14a252d') and
        w.worker_id not in excluded['excluded_worker_ids'] and
        w.worker_id.rsplit('-worker-',1)[0] not in excluded['excluded_worker_prefixes'] and
        w.metadata.tpu_name and w.metadata.tpu_name not in blocked_names]
    for worker in sorted(eligible,key=lambda w:(len(w.running_job_ids),w.worker_id)):
        allocated=[client.describe_task(JobName.from_string(t)).resources for t in worker.running_job_ids]
        if (worker.metadata.cpu_count*1000-sum(r.cpu_millicores for r in allocated)>=resources['cpus']*1000 and
            worker.metadata.memory_bytes-sum(r.memory_bytes for r in allocated)>=resources['memory_gib']*1024**3 and
            worker.metadata.disk_bytes-sum(r.disk_bytes for r in allocated)>=resources['disk_gib']*1024**3):return worker
    raise RuntimeError('No compatible existing reserved worker with declared headroom')


def observe(client,family,directory):
    from iris.cluster.types import JobName
    from iris.resources.state import is_job_finished
    job_id='/exedev/'+family['run_id'];known=[j for j in client.list_jobs(prefix=job_id,limit=3) if str(j.job_id)==job_id]
    if not known:
        # A persisted intent does not prove absence of a delayed effect. Never resubmit.
        write(directory/'observation.json',dict(job_id=job_id,state='handle_missing',observed=time.time()))
        return 'handle_missing'
    job=client.job(JobName.from_string(job_id));status=job.status()
    submission=directory/'submission.json'
    assert submission.exists(), 'Do not adopt an existing job without this controller intent'
    receipt=json.loads(submission.read_text());assert receipt['payload_sha256']==family['payload_sha256']
    assert status.resources.cpu_millicores==family['resources']['cpus']*1000
    if receipt['state']!='submitted':receipt['state']='observed_existing';write(submission,receipt)
    write(directory/'observation.json',dict(job_id=job_id,state=str(status.state),observed=time.time()))
    if not is_job_finished(status.state):return str(status.state)
    detail=job.task(0).describe();attempts=detail.status.attempts
    assert len(attempts)==1, 'No retries permitted'
    attempt=attempts[0];seconds=attempt.finished_at.epoch_seconds()-attempt.started_at.epoch_seconds()
    account=dict(job_id=job_id,state=str(status.state),attempts=1,exit_code=attempt.exit_code,
        allocated_cpu=detail.resources.cpu_millicores/1000,attempt_seconds=seconds,
        allocated_cpu_hours=seconds*detail.resources.cpu_millicores/1000/3600,
        output_archive=dataclasses.asdict(attempt)['output_archive'],model_calls=0)
    write(directory/'accounting.json',account)
    return str(status.state)


def submit(client,family,directory,files,budget_path,preflight=False):
    from iris.cluster.types import Entrypoint,EnvironmentSpec,JobName,ResourceSpec
    from iris.cluster.constraints import Constraint,ConstraintOp
    from iris.resources.state import is_job_finished
    from iris.rpc import job_pb2
    from rigging.secrets import SecretBehavior
    from rigging.timing import Duration
    from budget import Budget
    name=family['run_id'];job_id='/exedev/'+name
    assert not [j for j in client.list_jobs(prefix=job_id,limit=3) if str(j.job_id)==job_id], 'Known handle: observe, never replace'
    assert all(is_job_finished(j.state) for j in client.list_jobs(prefix='/exedev/biotasks39-',limit=50)), 'Serial cohort: active job must finish first'
    cleanup='primary_run_id' in family
    if cleanup:
        from iris.rpc import controller_pb2
        source=family['cleanup_target']
        workers=client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
        candidates=[w for w in workers if w.worker_id==source['worker_id'] and w.healthy and
            w.metadata.tpu_name==source['worker_tpu_name'] and w.metadata.provenance.base_commit.startswith('c7c14a252d')]
        assert len(candidates)==1, 'Cleanup requires the exact original healthy worker'
        worker=candidates[0]
        result=json.loads((directory.parent/'readback.json').read_text())
        assert result['run_id']==family['primary_run_id'] and result['archive_sha256']
    else:
        config=json.loads(files['family.json']);worker=choose_worker(client,config)
    r=family['resources']
    evidence=dict(job_id=job_id,worker_id=worker.worker_id,worker_tpu_name=worker.metadata.tpu_name,
        worker_base=worker.metadata.provenance.base_commit,tpu_worker_id=int(worker.metadata.tpu_worker_id or 0),
        payload_sha256=family['payload_sha256'],resources=r,new_capacity=False,model_calls=0,
        existing_job_policy='ERROR',attempts_allowed=1)
    if preflight:write(directory/'preflight.json',evidence);return evidence
    Budget(budget_path).verify_reserved(name)
    prior=json.loads((directory/'preflight.json').read_text());assert prior['payload_sha256']==evidence['payload_sha256']
    assert not (directory/'submission.json').exists(), 'Submission intent exists: observe only'
    evidence.update(state='submission_pending',intent_at=time.time());write(directory/'submission.json',evidence)
    program='cleanup_job.py' if cleanup else 'worker_job.py'
    env={'PYTHONDONTWRITEBYTECODE':'1','BIOTASKS_EXPECTED_WORKER':worker.worker_id}
    env.update({'BIOTASKS_CLEANUP_RUN':family['primary_run_id']} if cleanup else {'BIOTASKS_RUN_ID':name})
    job=client.submit(name=name,entrypoint=Entrypoint(command=['bash','-c','exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/'+program+'"'],workdir_files=files),
        resources=ResourceSpec(cpu=r['cpus'],memory=r['memory_gib']*1024**3,disk=r['disk_gib']*1024**3),
        environment=EnvironmentSpec(setup_scripts=[],env_vars=env,secret_behavior=SecretBehavior.ISOLATE),
        constraints=[Constraint.create(key='tpu-name',op=ConstraintOp.EQ,value=worker.metadata.tpu_name),
            Constraint.create(key='tpu-worker-id',op=ConstraintOp.EQ,value=int(worker.metadata.tpu_worker_id or 0))],
        scheduling_timeout=Duration.from_seconds(180),timeout=Duration.from_seconds(r['timeout_seconds']),
        max_retries_failure=0,max_retries_preemption=0,existing_job_policy=job_pb2.EXISTING_JOB_POLICY_ERROR,
        priority_band=job_pb2.PRIORITY_BAND_BATCH,container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,
        egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
    assert str(job.job_id)==job_id
    evidence['state']='submitted';write(directory/'submission.json',evidence)
    return evidence


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['preflight','submit','observe'])
    parser.add_argument('--family',required=True);parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--budget',required=True,type=Path);parser.add_argument('--cleanup',action='store_true');args=parser.parse_args()
    family,directory,files=load(args.family,args.cleanup)
    from iris.cli.connect import connect_controller
    from iris.client.client import IrisClient
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url,credentials=endpoint.credentials,timeout_ms=30000) as client:
            result=observe(client,family,directory) if args.action=='observe' else submit(client,family,directory,files,args.budget,args.action=='preflight')
    print(json.dumps(dict(action=args.action,family=args.family,result=result)))


if __name__=='__main__':main()
