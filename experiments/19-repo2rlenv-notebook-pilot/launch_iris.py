"""Submit the approved one-job pilot from committed inputs; never auto-resubmit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

EXPERIMENT = "experiments/19-repo2rlenv-notebook-pilot"


def frozen_file(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", revision + ":" + path], cwd=repo)


def payload(repo: Path, *, revision: str, seed: Path, upstream_archive: Path) -> dict[str, bytes]:
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/pilot-config.json"))
    if config["campaign_seconds"] != 7200 or config["cleanup_seconds"] != 300:
        raise ValueError("Execution duration differs from approved pilot")
    source = json.loads(frozen_file(repo, revision, EXPERIMENT + "/source-manifest.json"))
    seeds = json.loads(seed.read_text())
    if len(seeds) != 1 or seeds[0]["input_manifest"] != source:
        raise ValueError("Seed source manifest differs from checkpoint")
    files = {
        "biotasks.tar": subprocess.check_output(["git", "archive", revision], cwd=repo),
        "upstream.tar.gz": upstream_archive.read_bytes(),
        "seeds.json": seed.read_bytes(),
        "bootstrap.py": frozen_file(repo, revision, EXPERIMENT + "/iris_bootstrap.py"),
    }
    files["inputs.json"] = json.dumps(
        {
            "factory_revision": revision,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        },
        indent=2,
    ).encode()
    return files


def submit(
    client,
    *,
    repo: Path,
    revision: str,
    seed: Path,
    upstream_archive: Path,
    receipt: Path,
    token: str,
    daytona_key: str,
    artifact_prefix: str,
    endpoint_job: str,
    cluster: str,
):
    from iris.cluster.constraints import Constraint, ConstraintOp
    from iris.cluster.setup_scripts import default_setup_script
    from iris.cluster.types import Entrypoint, EnvironmentSpec, ResourceSpec
    from iris.rpc import job_pb2
    from rigging.timing import Duration

    if not token or not daytona_key or not artifact_prefix.startswith("s3://"):
        raise ValueError(
            "Explicit approved runtime credentials and private artifact destination required"
        )
    files = payload(repo, revision=revision, seed=seed, upstream_archive=upstream_archive)
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/pilot-config.json"))
    job_name = "biotasks19-" + config["campaign"]
    record = {
        "state": "submission_uncertain",
        "name": job_name,
        "factory_revision": revision,
        "inputs": json.loads(files["inputs.json"]),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x") as stream:
        json.dump(record, stream, indent=2)
    # Once this claim exists, an exception requires job reconciliation, never a
    # second submit call. Service credentials are only process environment values.
    job = client.submit(
        name=job_name,
        entrypoint=Entrypoint(command=["python", "bootstrap.py"], workdir_files=files),
        resources=ResourceSpec(cpu=2, memory=4 * 1024**3, disk=20 * 1024**3),
        environment=EnvironmentSpec(
            setup_scripts=[
                default_setup_script(
                    packages=["marin-iris"], pip_packages=["uv==0.12.21"], python_version="3.13"
                )
            ],
            env_vars={
                "GLM_BULK_TOKEN": token,
                "DAYTONA_API_KEY": daytona_key,
                "GLM_ENDPOINT_JOB": endpoint_job,
                "BIOTASKS_ARTIFACT_PREFIX": artifact_prefix.rstrip("/") + "/" + job_name,
                "BIOTASKS_IRIS_WORKER_ID": job_name,
                **{
                    key: "1"
                    for key in (
                        "OMP_NUM_THREADS",
                        "OPENBLAS_NUM_THREADS",
                        "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS",
                        "POLARS_MAX_THREADS",
                        "RAYON_NUM_THREADS",
                    )
                },
            },
        ),
        constraints=[Constraint.create(key="cluster", op=ConstraintOp.EQ, value=cluster)],
        timeout=Duration.from_seconds(7500),
        scheduling_timeout=Duration.from_seconds(600),
        max_retries_failure=0,
        max_retries_preemption=0,
        priority_band=job_pb2.PRIORITY_BAND_BATCH,
    )
    record.update(state="submitted", job_id=str(job.job_id))
    temporary = receipt.with_suffix(".submitted.tmp")
    temporary.write_text(json.dumps(record, indent=2))
    temporary.replace(receipt)
    return record
