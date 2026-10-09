"""Iris adapter for the frozen factory dispatcher; access is injected at runtime.

The caller owns the authenticated Iris client and campaign budget. This adapter
does not discover credentials, retry submissions, or alter generated tasks.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path


def checkpoint_file(repo: Path, revision: str, path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Exact factory commit required")
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


class IrisFactoryBackend:
    def __init__(
        self,
        client,
        repo: Path,
        runtime: Path,
        runtime_sha256: str,
        provider_config: Path,
        provider_sha256: str,
        token: str,
        endpoint_job: str,
        artifact_prefix: str,
        cluster: str,
    ):
        self.client = client
        self.repo = repo
        self.runtime = runtime.read_bytes()
        self.provider = provider_config.read_bytes()
        if hashlib.sha256(self.runtime).hexdigest() != runtime_sha256:
            raise ValueError("ZCode runtime hash mismatch")
        if hashlib.sha256(self.provider).hexdigest() != provider_sha256:
            raise ValueError("Provider configuration hash mismatch")
        if not token or not endpoint_job or not artifact_prefix.startswith("s3://"):
            raise ValueError("Runtime service access and durable artifact prefix required")
        self.token = token
        self.endpoint_job = endpoint_job
        self.artifact_prefix = artifact_prefix.rstrip("/")
        self.cluster = cluster

    def __call__(self, session: str, batch: dict, archive: Path) -> str:
        from iris.cluster.constraints import Constraint, ConstraintOp
        from iris.cluster.setup_scripts import default_setup_script
        from iris.cluster.types import Entrypoint, EnvironmentSpec, ResourceSpec
        from iris.rpc import job_pb2
        from rigging.timing import Duration

        _, seed, stage = session.split(":")
        spec = batch["entries"][seed]
        if stage != spec["stage"]:
            raise ValueError("Session stage mismatch")
        revision = batch["factory_revision"]
        prompt_name = spec["prompt_name"]
        if prompt_name not in {"notebook-task-v1", "notebook-review-v1", "notebook-repair-v1"}:
            raise ValueError("Unknown checkpointed prompt")
        prompt = checkpoint_file(self.repo, revision, f"src/biotasks/prompts/{prompt_name}.md")
        if prompt.decode() != spec["prompt"]:
            raise ValueError("Batch prompt does not match factory revision")
        name = "biotasks-factory-" + hashlib.sha256(session.encode()).hexdigest()[:32]
        files = {
            "_biotasks_smoke.py": checkpoint_file(
                self.repo, revision, "experiments/18-notebook-pipeline-v1/zcode_smoke.py"
            ),
            "zcode.cjs": self.runtime,
            "zcode-builtin.json": self.provider,
            "inputs.zip": archive.read_bytes(),
            "run-spec.json": (json.dumps(spec, indent=2) + "\n").encode(),
        }
        job = self.client.submit(
            name=name,
            entrypoint=Entrypoint(command=["python", "_biotasks_smoke.py"], workdir_files=files),
            resources=ResourceSpec(cpu=4, memory=8589934592, disk=10737418240),
            environment=EnvironmentSpec(
                setup_scripts=[
                    default_setup_script(packages=["marin-iris"], python_version="3.13")
                ],
                env_vars={
                    "BIOTASKS_ARTIFACT_PREFIX": self.artifact_prefix + "/" + name,
                    "GLM_BULK_TOKEN": self.token,
                    "GLM_ENDPOINT_JOB": self.endpoint_job,
                    "OMP_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                },
            ),
            constraints=[Constraint.create(key="cluster", op=ConstraintOp.EQ, value=self.cluster)],
            timeout=Duration.from_seconds(1800),
            scheduling_timeout=Duration.from_seconds(600),
            max_retries_failure=0,
            max_retries_preemption=0,
            priority_band=job_pb2.PRIORITY_BAND_BATCH,
        )
        return str(job.job_id)
