"""Single-entrypoint, bounded research campaign on existing reserved Iris CPUs.

Requires Iris/rigging on PYTHONPATH and an authenticated gcloud executable.
Private state contains infrastructure identities; never publish that directory.
No retries, replacement inputs, new capacity, models, or per-PR intervention.
"""

import argparse
import dataclasses
import datetime
import hashlib
import io
import json
import subprocess
import tarfile
import time
from pathlib import Path

import zstandard
from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.constraints import Constraint, ConstraintOp
from iris.cluster.types import Entrypoint, EnvironmentSpec, JobName, ResourceSpec
from iris.rpc import controller_pb2, job_pb2
from iris.resources.state import is_job_finished
from rigging.timing import Duration

ROOT = Path(__file__).resolve().parent


def save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, default=str) + "\n")
    temporary.replace(path)


def download(archive, destination, gcloud):
    assert archive["state"] == "uploaded"
    assert archive["size_bytes"] < 50 * 1024**2
    path = destination / "outputs.tar.zst"
    subprocess.run([gcloud, "storage", "cp", archive["uri"], str(path)],
                   capture_output=True, check=True, timeout=120)
    raw = path.read_bytes()
    assert len(raw) == archive["size_bytes"]
    assert hashlib.sha256(raw).hexdigest() == archive["sha256"]
    extracted = 0
    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as stream:
        with tarfile.open(fileobj=stream, mode="r|") as bundle:
            for member in bundle:
                if not member.isfile():
                    continue
                assert member.size < 20 * 1024**2
                extracted += member.size
                assert extracted < 200 * 1024**2
                assert Path(member.name).name == member.name
                (destination / member.name).write_bytes(bundle.extractfile(member).read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--iris-config", type=Path, required=True)
    parser.add_argument("--gcloud", required=True)
    args = parser.parse_args()
    campaign = json.loads(args.campaign.read_text())
    if "launcher_sha256" in campaign:
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == campaign["launcher_sha256"]
    assert campaign["max_concurrent_workers"] in (1, 2)
    assert campaign["model_calls"] == 0
    files = {name: (ROOT / name).read_bytes() for name in campaign["code_sha256"]}
    for name, data in files.items():
        assert hashlib.sha256(data).hexdigest() == campaign["code_sha256"][name], name
    manifests = []
    for filename, expected in campaign["input_sha256"].items():
        raw = (ROOT / filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, filename
        manifest = json.loads(raw)
        for row in manifest["prs"]:
            row["diff"] = (ROOT / row["diff_path"]).read_text()
            assert hashlib.sha256(row["diff"].encode()).hexdigest() == row["diff_sha256"]
        manifests.append(manifest)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    campaign_hash = hashlib.sha256(args.campaign.read_bytes()).hexdigest()
    state_file = args.state_dir / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {
        "campaign_sha256": campaign_hash, "jobs": {},
    }
    assert state["campaign_sha256"] == campaign_hash
    with connect_controller(config_file=args.iris_config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials,
                               timeout_ms=30000) as client:
            while True:
                active = 0
                for manifest in manifests:
                    name = manifest["run_id"]
                    receipt = state["jobs"].get(name)
                    if receipt is None or receipt.get("terminal_recorded"):
                        continue
                    # The deterministic name is saved before submit. An uncertain
                    # submission is inspected on resume, never blindly retried.
                    job = client.job(JobName.from_string(receipt["job_id"]))
                    status = job.status()
                    receipt["state"] = status.state.name
                    if not is_job_finished(status.state):
                        active += 1
                        continue
                    attempts = [dataclasses.asdict(a) for a in job.task(0).describe().status.attempts]
                    receipt["attempts"] = attempts
                    receipt["error_message"] = status.error_message
                    receipt["logs"] = [r.data for r in job.logs(substring="BIOTASKS24_", max_lines=10)]
                    archive = attempts[-1]["output_archive"] if attempts else None
                    if not archive or archive["state"] != "uploaded":
                        receipt["readback_error"] = "terminal_without_uploaded_archive"
                        receipt["terminal_recorded"] = True
                        receipt["readback_verified"] = False
                        save(state_file, state)
                        print(json.dumps({"run_id": name, "state": receipt["state"],
                                          "readback_verified": False}), flush=True)
                        continue
                    dest = args.state_dir / name
                    dest.mkdir(exist_ok=True)
                    download(archive, dest, args.gcloud)
                    report = dest / "development-result.json"
                    if report.exists():
                        expected = [
                            line.split("BIOTASKS24_DEVELOPMENT_SHA256 ", 1)[1].strip()
                            for line in receipt["logs"] if "BIOTASKS24_DEVELOPMENT_SHA256 " in line
                        ]
                        assert len(expected) == 1
                        assert hashlib.sha256(report.read_bytes()).hexdigest() == expected[0]
                    receipt["readback_verified"] = True
                    receipt["terminal_recorded"] = True
                    save(state_file, state)
                    print(json.dumps({"run_id": name, "state": receipt["state"],
                                      "readback_verified": True}), flush=True)
                for manifest in manifests:
                    name = manifest["run_id"]
                    if name in state["jobs"] or active >= campaign["max_concurrent_workers"]:
                        continue
                    workers = client.list_workers(
                        query=controller_pb2.Controller.WorkerQuery(limit=500)
                    )
                    eligible = [w for w in workers if w.healthy and
                                "v4-reserved" in w.scale_group and w.metadata.tpu_name
                                and w.metadata.provenance.base_commit == campaign["required_worker_base_commit"]
                                and w.metadata.provenance.tree_hash == campaign["required_worker_tree_hash"]
                                and not w.metadata.provenance.dirty]
                    assert eligible, "No existing healthy reserved TRC worker"
                    worker = min(eligible, key=lambda w: (len(w.running_job_ids), w.worker_id))
                    receipt = {
                        "job_id": f"/exedev/{name}", "state": "submission_pending",
                        "existing_tpu_name": worker.metadata.tpu_name,
                        "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    state["jobs"][name] = receipt
                    save(state_file, state)
                    workdir_files = dict(files)
                    workdir_files["development-input.json"] = (json.dumps(manifest) + "\n").encode()
                    job = client.submit(
                        name=name,
                        entrypoint=Entrypoint(command=[
                            "bash", "-c",
                            'exec env -i PATH=/usr/local/bin:/usr/bin:/bin '
                            'IRIS_OUTPUT_DIR="$IRIS_OUTPUT_DIR" OMP_NUM_THREADS=1 '
                            'OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 '
                            '"$IRIS_PYTHON" -u "$IRIS_WORKDIR/run_native_development.py"',
                        ], workdir_files=workdir_files),
                        resources=ResourceSpec(cpu=3, memory="10GB", disk="30GB"),
                        environment=EnvironmentSpec(setup_scripts=[], env_vars={}),
                        constraints=[Constraint.create(key="tpu-name", op=ConstraintOp.EQ,
                                                       value=worker.metadata.tpu_name),
                                     Constraint.create(key="tpu-worker-id", op=ConstraintOp.EQ,
                                                       value=int(worker.metadata.tpu_worker_id or 0))],
                        scheduling_timeout=Duration.from_seconds(180),
                        timeout=Duration.from_seconds(4200),
                        max_retries_failure=0, max_retries_preemption=0,
                        priority_band=job_pb2.PRIORITY_BAND_BATCH,
                        container_profile=job_pb2.CONTAINER_PROFILE_DOCKER_ACCESS,
                        egress_policy=job_pb2.EGRESS_POLICY_INTERNET,
                    )
                    assert str(job.job_id) == receipt["job_id"]
                    receipt["state"] = "submitted"
                    save(state_file, state)
                    active += 1
                    print(json.dumps({"run_id": name, "state": "submitted"}), flush=True)
                if all(state["jobs"].get(m["run_id"], {}).get("terminal_recorded")
                       for m in manifests):
                    break
                save(state_file, state)
                # Sparse remote status checks, not a per-minute local poller.
                time.sleep(180)


if __name__ == "__main__":
    main()
