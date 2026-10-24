"""Standalone JSON bridge, compatible with the configured Iris Python >=3.12.

This module never imports the parent CLI, Harbor or model clients. Credentials
remain in the local Iris transport; only an explicit isolated environment enters
the submitted worker. Keep SDK imports dynamic so the main package does not
require a particular Iris installation merely to inspect/plan exports.
"""

import dataclasses
import importlib
import importlib.metadata
import json
import platform
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from biotasks.validation.files import MAX_ARCHIVE, json_sha, lock, require, sha, write_json


def module(name: str) -> Any:
    return importlib.import_module(name)


def fingerprint() -> dict[str, Any]:
    sources = {}
    versions = {}
    for name in ("iris", "rigging"):
        package = module(name)
        root = Path(package.__file__).resolve().parent
        rows = {}
        total = 0
        for file in sorted(root.rglob("*.py")):
            total += file.stat().st_size
            require(total <= MAX_ARCHIVE and len(rows) < 3000, "SDK source tree exceeds limit")
            rows[file.relative_to(root).as_posix()] = sha(file)
        sources[name] = {"root": str(root), "files": len(rows), "sha256": json_sha(rows)}
        names = importlib.metadata.packages_distributions().get(name, [])
        versions[name] = {n: importlib.metadata.version(n) for n in names}
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "source": sources,
        "versions": versions,
    }


@contextmanager
def connect(config: str) -> Iterator[Any]:
    connector = module("iris.cli.connect").connect_controller
    client_type = module("iris.client.client").IrisClient
    with connector(config_file=Path(config)) as endpoint:
        with client_type.remote(
            endpoint.url, credentials=endpoint.credentials, timeout_ms=30000
        ) as client:
            yield client


def exact_job(client: Any, name: str) -> Any:
    return next(
        (job for job in client.list_jobs(prefix=name, limit=3) if str(job.job_id) == name), None
    )


def choose_worker(
    client: Any,
    backend: dict[str, Any],
    resources: dict[str, Any],
    target: dict[str, Any] | None = None,
) -> Any:
    workers = client.list_workers(
        query=module("iris.rpc.controller_pb2").Controller.WorkerQuery(limit=500)
    )
    eligible = [
        w
        for w in workers
        if w.healthy
        and "v4-reserved" in w.scale_group
        and not w.metadata.provenance.dirty
        and w.metadata.provenance.base_commit.startswith(backend["worker_revision"])
        and w.worker_id not in backend.get("excluded_worker_ids", [])
        and w.metadata.tpu_name
    ]
    if target:
        eligible = [
            w
            for w in eligible
            if w.worker_id == target["worker_id"]
            and w.metadata.tpu_name == target["worker_tpu_name"]
        ]
    job_name = module("iris.cluster.types").JobName
    for worker in sorted(eligible, key=lambda w: (len(w.running_job_ids), w.worker_id)):
        allocated = [
            client.describe_task(job_name.from_string(t)).resources for t in worker.running_job_ids
        ]
        if (
            worker.metadata.cpu_count * 1000 - sum(r.cpu_millicores for r in allocated)
            >= resources["cpus"] * 1000
            and worker.metadata.memory_bytes - sum(r.memory_bytes for r in allocated)
            >= resources["memory_gib"] * 1024**3
            and worker.metadata.disk_bytes - sum(r.disk_bytes for r in allocated)
            >= resources["disk_gib"] * 1024**3
        ):
            return worker
    raise RuntimeError("No compatible existing reserved worker with declared headroom")


def preflight(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    group = request["group"]
    require(
        exact_job(client, "/exedev/" + group["run_id"]) is None,
        "Existing handle without this run's intent",
    )
    worker = choose_worker(client, request["backend"], group["resources"], request.get("target"))
    return {
        "run_id": group["run_id"],
        "worker_id": worker.worker_id,
        "worker_tpu_name": worker.metadata.tpu_name,
        "worker_base": worker.metadata.provenance.base_commit,
        "resources": group["resources"],
        "payload_sha256": request["payload_sha256"],
        "existing_job_policy": "ERROR",
        "attempts_allowed": 1,
        "new_capacity": False,
        "model_calls": 0,
    }


def _submit(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    intent = Path(request["submission_file"])
    require(not intent.exists(), "Submission intent exists; query the existing handle")
    receipt = preflight(client, request)
    group = request["group"]
    backend = request["backend"]
    # Re-observe/select immediately before persisting the immutable RPC intent.
    worker = choose_worker(client, backend, group["resources"], request.get("target"))
    directory = Path(request["payload_directory"])
    payload = {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    }
    require(set(payload) == set(request["payload_sha256"]), "Payload files changed")
    require(
        all(sha(directory / n) == v for n, v in request["payload_sha256"].items()),
        "Payload bytes changed",
    )
    receipt.update(
        worker_id=worker.worker_id,
        worker_tpu_name=worker.metadata.tpu_name,
        worker_base=worker.metadata.provenance.base_commit,
        tpu_worker_id=int(worker.metadata.tpu_worker_id or 0),
        job_id="/exedev/" + group["run_id"],
        state="submission_pending",
        intent_at=time.time(),
    )
    write_json(intent, receipt)
    types = module("iris.cluster.types")
    constraints = module("iris.cluster.constraints")
    protocol = module("iris.rpc.job_pb2")
    duration = module("rigging.timing").Duration
    secret_behavior = module("rigging.secrets").SecretBehavior
    resources = group["resources"]
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "BIOTASKS_EXPECTED_WORKER": worker.worker_id,
        "BIOTASKS_RUN_ID": request.get("primary_run_id", group["run_id"]),
    }
    command = 'PYTHONPATH="$IRIS_WORKDIR" exec "$IRIS_PYTHON" -u -m biotasks.validation.worker.job'
    job = client.submit(
        name=group["run_id"],
        entrypoint=types.Entrypoint(command=["bash", "-c", command], workdir_files=payload),
        resources=types.ResourceSpec(
            cpu=resources["cpus"],
            memory=resources["memory_gib"] * 1024**3,
            disk=resources["disk_gib"] * 1024**3,
        ),
        environment=types.EnvironmentSpec(
            setup_scripts=[], env_vars=environment, secret_behavior=secret_behavior.ISOLATE
        ),
        constraints=[
            constraints.Constraint.create(
                key="tpu-name", op=constraints.ConstraintOp.EQ, value=worker.metadata.tpu_name
            ),
            constraints.Constraint.create(
                key="tpu-worker-id",
                op=constraints.ConstraintOp.EQ,
                value=int(worker.metadata.tpu_worker_id or 0),
            ),
        ],
        scheduling_timeout=duration.from_seconds(180),
        timeout=duration.from_seconds(resources["timeout_seconds"]),
        max_retries_failure=0,
        max_retries_preemption=0,
        existing_job_policy=protocol.EXISTING_JOB_POLICY_ERROR,
        priority_band=protocol.PRIORITY_BAND_BATCH,
        container_profile=protocol.CONTAINER_PROFILE_DOCKER_ACCESS,
        egress_policy=protocol.EGRESS_POLICY_INTERNET,
    )
    require(str(job.job_id) == receipt["job_id"], "Unexpected returned job")
    receipt["state"] = "submitted"
    write_json(intent, receipt)
    return receipt


def submit(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    # Remains held if the parent CLI dies while its transport child is alive.
    # A recovery cannot race that child's preflight / intent / submit sequence.
    path = Path(request["submission_file"])
    with lock(path.with_suffix(".rpc.lock")):
        return _submit(client, request)


def observe(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    job_id = "/exedev/" + request["group"]["run_id"]
    if exact_job(client, job_id) is None:
        return {"state": "handle_missing", "job_id": job_id}
    job = client.job(module("iris.cluster.types").JobName.from_string(job_id))
    state = job.status()
    if not module("iris.resources.state").is_job_finished(state.state):
        return {"state": str(state.state), "job_id": job_id}
    task = job.task(0).describe()
    attempts = task.status.attempts
    require(len(attempts) <= 1, "Unexpected retry; preserve evidence and stop")
    if not attempts:
        return {
            "job_id": job_id,
            "state": str(state.state),
            "terminal": True,
            "attempts": 0,
            "allocated_cpu_hours": 0,
            "output_archive": {"state": "empty"},
            "verified_no_creation": True,
            "reason": "Terminal scheduler state with no task attempts",
        }
    attempt = attempts[0]
    seconds = attempt.finished_at.epoch_seconds() - attempt.started_at.epoch_seconds()
    require(
        seconds >= 0
        and task.resources.cpu_millicores == request["group"]["resources"]["cpus"] * 1000,
        "Remote resource/accounting mismatch",
    )
    return {
        "job_id": job_id,
        "state": str(state.state),
        "terminal": True,
        "attempts": 1,
        "exit_code": attempt.exit_code,
        "attempt_seconds": seconds,
        "allocated_cpu": task.resources.cpu_millicores / 1000,
        "allocated_cpu_hours": seconds * task.resources.cpu_millicores / 1000 / 3600,
        "output_archive": dataclasses.asdict(attempt)["output_archive"],
        "model_calls": 0,
    }


def logs(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    name = module("iris.cluster.types").JobName.from_string("/exedev/" + request["group"]["run_id"])
    rows = client.job(name).logs(max_lines=100, tail=False)
    return {
        "logs": [
            {
                "timestamp_epoch_seconds": r.timestamp.epoch_seconds(),
                "source": r.source,
                "data": r.data,
                "attempt_id": r.attempt_id,
                "key": r.key,
            }
            for r in rows
        ]
    }


def main() -> None:
    request = json.load(sys.stdin)
    if request["action"] == "fingerprint":
        result = fingerprint()
    else:
        with connect(request["backend"]["config"]) as client:
            action = request["action"]
            require(action in ("preflight", "submit", "observe", "logs"), "Unknown backend action")
            result = {"preflight": preflight, "submit": submit, "observe": observe, "logs": logs}[
                action
            ](client, request)
    print("BIOTASKS_VALIDATION_RESULT=" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
