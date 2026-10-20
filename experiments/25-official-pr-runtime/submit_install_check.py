"""Submit once to existing reserved TRC capacity; receipt is private local state."""

import argparse
import json
from pathlib import Path

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from rigging.timing import Duration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    assert not args.receipt.exists(), "Inspect the existing submission; do not resubmit"
    root = Path(__file__).resolve().parent
    paths = [root / "trc_install_check.py", root / "docker_resource_wrapper.py",
             *sorted((root / "proposed-configs").glob("*.json"))]
    files = {str(path.relative_to(root)): path.read_bytes() for path in paths}
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            workers = client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible = [w for w in workers if w.healthy and "v4-reserved" in w.scale_group
                        and w.metadata.tpu_name
                        and w.metadata.provenance.base_commit.startswith("205558e1a7")
                        and not w.metadata.provenance.dirty]
            assert eligible, "No eligible existing reserved worker"
            worker = min(eligible, key=lambda w: (len(w.running_job_ids), w.worker_id))
            name = "biotasks25-install-001"
            receipt = {"job_id": f"/exedev/{name}", "state": "submission_pending",
                       "worker_id": worker.worker_id, "cpu": 4, "memory": "16GB",
                       "timeout_seconds": 1800, "model_calls": 0}
            with args.receipt.open("x") as handle:
                handle.write(json.dumps(receipt, indent=2) + "\n")
            job = client.submit(
                name=name,
                entrypoint=Entrypoint(command=["bash", "-c",
                    'exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/trc_install_check.py"'], workdir_files=files),
                resources=ResourceSpec(cpu=4, memory="16GB", disk="30GB"),
                environment=EnvironmentSpec(setup_scripts=[], env_vars={}),
                constraints=[Constraint.create(key="tpu-name", op=ConstraintOp.EQ,
                                               value=worker.metadata.tpu_name),
                             Constraint.create(key="tpu-worker-id", op=ConstraintOp.EQ,
                                               value=int(worker.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180), timeout=Duration.from_seconds(1800),
                max_retries_failure=0, max_retries_preemption=0,
                priority_band=job_pb2.PRIORITY_BAND_BATCH,
                container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,
                egress_policy=job_pb2.EGRESS_POLICY_INTERNET,
            )
            assert str(job.job_id) == receipt["job_id"]
            receipt["state"] = "submitted"
            args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
            print(receipt["job_id"])


if __name__ == "__main__":
    main()
