"""Submit one metadata-only task to an existing reserved CPU host; no Docker/model access."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, JobName, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from rigging.timing import Duration

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    assert not args.receipt.exists(), 'Inspect the same handle; never submit twice'
    assert os.environ.get('GH_TOKEN')
    args.receipt.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    files = {name: (ROOT / name).read_bytes() for name in ['inventory.py', 'history-counts.json']}
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            assert not client.list_jobs(prefix='/exedev/biotasks28-history-inventory-001', limit=2), 'Existing name; observe it instead'
            workers = client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible = [w for w in workers if w.healthy and 'v4-reserved' in w.scale_group
                and w.metadata.tpu_name and not w.metadata.provenance.dirty]
            worker = None
            for candidate in sorted(eligible, key=lambda w: (not bool(w.running_job_ids), len(w.running_job_ids), w.worker_id)):
                allocated = [client.describe_task(JobName.from_string(t)).resources for t in candidate.running_job_ids]
                if (candidate.metadata.cpu_count * 1000 - sum(r.cpu_millicores for r in allocated) >= 1000
                    and candidate.metadata.memory_bytes - sum(r.memory_bytes for r in allocated) >= 2 * 1024**3
                    and candidate.metadata.disk_bytes - sum(r.disk_bytes for r in allocated) >= 5 * 1024**3):
                    worker = candidate
                    break
            assert worker is not None, 'No existing reserved host with headroom'
            run = 'biotasks28-history-inventory-001'
            receipt = {'job_id': '/exedev/' + run, 'state': 'submission_pending',
                'worker_id': worker.worker_id, 'worker_base': worker.metadata.provenance.base_commit,
                'existing_clean_reserved_worker': True, 'new_capacity': False,
                'cpu': 1, 'memory_gib': 2, 'disk_gib': 5, 'timeout_seconds': 1200,
                'container_profile': 'SANDBOX', 'egress': 'INTERNET',
                'docker_socket': False, 'openrouter_credential_supplied': False,
                'model_calls': 0, 'attempts_allowed': 1,
                'input_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
            with args.receipt.open('x') as output:
                output.write(json.dumps(receipt, indent=2) + '\n')
            job = client.submit(name=run,
                entrypoint=Entrypoint(command=['bash', '-c',
                    'exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/inventory.py" --remote-worker '
                    '--state-dir "$IRIS_OUTPUT_DIR/pages" --report-dir "$IRIS_OUTPUT_DIR"'], workdir_files=files),
                resources=ResourceSpec(cpu=1, memory='2GB', disk='5GB'),
                environment=EnvironmentSpec(setup_scripts=[], env_vars={'GH_TOKEN': os.environ['GH_TOKEN']}),
                constraints=[Constraint.create(key='tpu-name', op=ConstraintOp.EQ, value=worker.metadata.tpu_name),
                    Constraint.create(key='tpu-worker-id', op=ConstraintOp.EQ, value=int(worker.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180), timeout=Duration.from_seconds(1200),
                max_retries_failure=0, max_retries_preemption=0, priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_SANDBOX, egress_policy=job_pb2.EGRESS_POLICY_INTERNET)
            assert str(job.job_id) == receipt['job_id']
            receipt['state'] = 'submitted'
            args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
