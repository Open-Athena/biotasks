"""Submit one frozen history run to existing reserved capacity; serialize outside this helper."""

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, JobName, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from rigging.timing import Duration

from payload import BASE, build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--slug', required=True)
    parser.add_argument('--remaining-usd', required=True)
    args = parser.parse_args()
    selected = next(r for r in json.loads((BASE / 'cohort.json').read_text()) if r['slug'] == args.slug)
    files = build(selected, Decimal(args.remaining_usd))
    assert os.environ.get('OPENROUTER_API_KEY') and os.environ.get('GH_TOKEN')
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = args.state_dir / (run + '-receipt.json'); assert not target.exists()
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            existing = client.list_jobs(prefix='/exedev/biotasks28-history-', limit=50)
            from iris.resources.state import is_job_finished
            assert all(is_job_finished(row.state) for row in existing), 'Observe active history run; do not overlap'
            assert not client.list_jobs(prefix='/exedev/' + run, limit=2), 'Existing handle; never resubmit'
            workers = client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible = [w for w in workers if w.healthy and 'v4-reserved' in w.scale_group
                and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            worker = None
            for candidate in sorted(eligible, key=lambda w: (not bool(w.running_job_ids), len(w.running_job_ids), w.worker_id)):
                allocations = [client.describe_task(JobName.from_string(t)).resources for t in candidate.running_job_ids]
                if (candidate.metadata.cpu_count * 1000 - sum(r.cpu_millicores for r in allocations) >= 4000
                    and candidate.metadata.memory_bytes - sum(r.memory_bytes for r in allocations) >= 16 * 1024**3
                    and candidate.metadata.disk_bytes - sum(r.disk_bytes for r in allocations) >= 30 * 1024**3):
                    worker = candidate; break
            assert worker is not None, 'No existing reserved worker has headroom'
            receipt = {'job_id': '/exedev/' + run, 'state': 'submission_pending', 'worker_id': worker.worker_id,
                'worker_base': worker.metadata.provenance.base_commit, 'new_capacity': False,
                'repo': selected['repo'], 'repo_ref': selected['ref'], 'remaining_openrouter_usd': args.remaining_usd,
                'source_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'cpu': 4, 'memory_gib': 16, 'disk_gib': 30, 'timeout_seconds': 9000,
                'attempts_allowed': 1, 'input_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}}
            with target.open('x') as output: output.write(json.dumps(receipt, indent=2) + '\n')
            job = client.submit(name=run,
                entrypoint=Entrypoint(command=['bash', '-c', 'exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/supervisor.py"'], workdir_files=files),
                resources=ResourceSpec(cpu=4, memory='16GB', disk='30GB'),
                environment=EnvironmentSpec(setup_scripts=[], env_vars={'BIOTASKS_RUN_ID': run,
                    'BIOTASKS_PHASE': 'generate', 'GH_TOKEN': os.environ['GH_TOKEN'],
                    'OPENROUTER_API_KEY': os.environ['OPENROUTER_API_KEY']}),
                constraints=[Constraint.create(key='tpu-name', op=ConstraintOp.EQ, value=worker.metadata.tpu_name),
                    Constraint.create(key='tpu-worker-id', op=ConstraintOp.EQ, value=int(worker.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180), timeout=Duration.from_seconds(9000),
                max_retries_failure=0, max_retries_preemption=0, priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS, egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id) == receipt['job_id']
            receipt['state'] = 'submitted'; target.write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps({k: v for k, v in receipt.items() if k != 'input_sha256'}), flush=True)


if __name__ == '__main__':
    main()
