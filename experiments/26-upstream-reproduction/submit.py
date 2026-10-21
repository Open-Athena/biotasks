"""Submit once to existing reserved TRC capacity; receipt is private local state."""

import argparse
import json
import os
from pathlib import Path

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, JobName, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from rigging.timing import Duration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", choices=["replay", "generate"], required=True)
    args = parser.parse_args()
    assert not args.receipt.exists(), "Inspect the existing submission; do not resubmit"
    root = Path(__file__).resolve().parent
    paths = [root / name for name in ["supervisor.py", "setup_controller.sh", "harbor_docker.py",
             "native_docker.py", "run_controls.py", "run_generation.py", "pins.json"]]
    paths += sorted((root / "native-configs").glob("*.json"))
    paths += sorted(p for p in (root / "published").rglob("*") if p.is_file())
    files = {str(path.relative_to(root)): path.read_bytes() for path in paths}
    pins = json.loads((root / "pins.json").read_text())
    runtime = pins["replay_timeout_seconds" if args.phase == "replay" else "generation_timeout_seconds"]
    entrypoint = "supervisor.py"
    env_vars = {"BIOTASKS_RUN_ID": args.run_id, "BIOTASKS_PHASE": args.phase}
    if args.phase == "generate":
        assert os.environ.get("OPENROUTER_API_KEY") and os.environ.get("GH_TOKEN")
        env_vars["OPENROUTER_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
        env_vars["GH_TOKEN"] = os.environ["GH_TOKEN"]
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            workers = client.list_workers(query=controller_pb2.Controller.WorkerQuery(limit=500))
            eligible = [w for w in workers if w.healthy and "v4-reserved" in w.scale_group
                        and w.metadata.tpu_name
                        and w.metadata.provenance.base_commit.startswith("205558e1a7")
                        and not w.metadata.provenance.dirty]
            assert eligible, "No eligible existing reserved worker"
            # Prefer an existing occupied host to an idle host being reclaimed.
            worker = None
            for candidate in sorted(eligible, key=lambda w: (not bool(w.running_job_ids), len(w.running_job_ids), w.worker_id)):
                allocations = [client.describe_task(JobName.from_string(t)).resources for t in candidate.running_job_ids]
                if (candidate.metadata.cpu_count * 1000 - sum(r.cpu_millicores for r in allocations) >= 4000
                    and candidate.metadata.memory_bytes - sum(r.memory_bytes for r in allocations) >= 16 * 1024**3
                    and candidate.metadata.disk_bytes - sum(r.disk_bytes for r in allocations) >= 30 * 1024**3):
                    worker = candidate
                    break
            assert worker is not None, "No existing reserved worker with sufficient headroom"
            name = args.run_id
            receipt = {"job_id": f"/exedev/{name}", "state": "submission_pending",
                       "worker_id": worker.worker_id, "cpu": 4, "memory": "16GB",
                       "timeout_seconds": runtime, "phase": args.phase}
            with args.receipt.open("x") as handle:
                handle.write(json.dumps(receipt, indent=2) + "\n")
            job = client.submit(
                name=name,
                entrypoint=Entrypoint(command=["bash", "-c",
                    f'exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/{entrypoint}"'], workdir_files=files),
                resources=ResourceSpec(cpu=4, memory="16GB", disk="30GB"),
                environment=EnvironmentSpec(setup_scripts=[], env_vars=env_vars),
                constraints=[Constraint.create(key="tpu-name", op=ConstraintOp.EQ,
                                               value=worker.metadata.tpu_name),
                             Constraint.create(key="tpu-worker-id", op=ConstraintOp.EQ,
                                               value=int(worker.metadata.tpu_worker_id or 0))],
                scheduling_timeout=Duration.from_seconds(180), timeout=Duration.from_seconds(runtime),
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
