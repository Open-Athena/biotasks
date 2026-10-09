"""Iris adapter for the frozen factory dispatcher; access is injected at runtime.

The caller owns the authenticated Iris client and campaign budget. This adapter
does not discover credentials, retry submissions, or alter generated tasks.
"""

import hashlib
import io
import json
import re
import subprocess
import zipfile
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
        daytona_key: str | None = None,
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
        self.daytona_key = daytona_key

    def __call__(self, session: str, batch: dict, archive: Path) -> str:
        from iris.cluster.constraints import Constraint, ConstraintOp
        from iris.cluster.setup_scripts import default_setup_script
        from iris.cluster.types import Entrypoint, EnvironmentSpec, ResourceSpec
        from iris.rpc import job_pb2
        from rigging.timing import Duration

        _, seed, slot = session.split(":")
        spec = batch["entries"][seed]
        whole_seed = batch.get("execution_mode") == "seed_pipeline"
        if slot != ("seed_pipeline" if whole_seed else spec.get("stage_slot", spec["stage"])):
            raise ValueError("Session stage mismatch")
        revision = batch["factory_revision"]
        prompt_name = spec["prompt_name"]
        if prompt_name not in {
            "notebook-task-v1",
            "notebook-review-v1",
            "notebook-repair-v1",
            "notebook-specification-v1",
            "notebook-construction-v1",
        }:
            raise ValueError("Unknown checkpointed prompt")
        prompt = checkpoint_file(self.repo, revision, f"src/biotasks/prompts/{prompt_name}.md")
        if prompt.decode() != spec["prompt"]:
            raise ValueError("Batch prompt does not match factory revision")
        job_name = "biotasks-factory-" + hashlib.sha256(session.encode()).hexdigest()[:32]
        files = {
            "_biotasks_smoke.py": checkpoint_file(
                self.repo, revision, "experiments/18-notebook-pipeline-v1/zcode_smoke.py"
            ),
            "zcode.cjs": self.runtime,
            "zcode-builtin.json": self.provider,
            "run-spec.json": (json.dumps(spec, indent=2) + "\n").encode(),
        }
        command = ["python", "_biotasks_smoke.py"]
        if slot in {"authoring", "specification", "seed_pipeline"}:
            files["inputs.zip"] = archive.read_bytes()
        else:
            files["handoff.zip"] = archive.read_bytes()
            for script in ("prepare_worker_handoff.py", "restore_authoring.py"):
                files[script] = checkpoint_file(
                    self.repo, revision, f"experiments/18-notebook-pipeline-v1/{script}"
                )
            command = ["python", "prepare_worker_handoff.py"]
        extra_env = {}
        timeout_seconds = 1800
        if whole_seed:
            if not self.daytona_key:
                raise ValueError("Whole-seed execution requires approved Daytona access")
            files.pop("_biotasks_smoke.py")
            for script in (
                "seed_pipeline_bootstrap.py", "seed_pipeline_worker.py", "zcode_smoke.py", "harbor_worker.py"
            ):
                files[script] = checkpoint_file(
                    self.repo, revision, f"experiments/18-notebook-pipeline-v1/{script}"
                )
            package_paths = [
                line
                for line in subprocess.run(
                    ["git", "ls-tree", "-r", "--name-only", revision, "src/biotasks"],
                    cwd=self.repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.splitlines()
                if line.endswith((".py", ".md"))
            ]
            # Keep package directories inside one flat workdir entry. Kubernetes
            # ConfigMap mounts expose nested directories as symlinks, which a
            # staging walk may skip. Zip import also avoids an ambient package.
            package = io.BytesIO()
            with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as target:
                for path in package_paths:
                    target.writestr(
                        path.removeprefix("src/"), checkpoint_file(self.repo, revision, path)
                    )
            files["factory-runtime.zip"] = package.getvalue()
            bundle = io.BytesIO()
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as target:
                with zipfile.ZipFile(io.BytesIO(files["factory-runtime.zip"])) as runtime:
                    for name in runtime.namelist():
                        target.writestr(name, runtime.read(name))
                for name in (
                    "control_agent.py",
                    "harbor_job.py",
                    "harbor_pi_remote.py",
                    "network_probe.py",
                    "pi_remote.ts",
                    "remote_paths.mjs",
                    "restore_authoring.py",
                    "retained_daytona.py",
                    "native_suite.py",
                ):
                    target.writestr(
                        name,
                        checkpoint_file(
                            self.repo, revision, f"experiments/18-notebook-pipeline-v1/{name}"
                        ),
                    )
            files["harbor-input.zip"] = bundle.getvalue()
            for template in batch["stage_templates"].values():
                pinned = checkpoint_file(
                    self.repo, revision, f"src/biotasks/prompts/{template['prompt_name']}.md"
                )
                if pinned.decode() != template["prompt"]:
                    raise ValueError("A stage prompt differs from the frozen factory")
            pipeline = {
                "seed": seed,
                "factory_revision": revision,
                "workflow_version": batch["workflow_version"],
                "stage_templates": batch["stage_templates"],
                "input_zip_sha256": spec["input_zip_sha256"],
                **batch["seed_execution"],
            }
            files["pipeline.json"] = (json.dumps(pipeline, indent=2) + "\n").encode()
            command = ["python", "seed_pipeline_bootstrap.py"]
            extra_env = {"DAYTONA_API_KEY": self.daytona_key}
            timeout_seconds = pipeline["seed_timeout_seconds"] + 300
        job = self.client.submit(
            name=job_name,
            entrypoint=Entrypoint(command=command, workdir_files=files),
            resources=ResourceSpec(cpu=4, memory=8589934592, disk=10737418240),
            environment=EnvironmentSpec(
                setup_scripts=[
                    default_setup_script(packages=["marin-iris"], python_version="3.13")
                ],
                env_vars={
                    "BIOTASKS_ARTIFACT_PREFIX": self.artifact_prefix + "/" + job_name,
                    "GLM_BULK_TOKEN": self.token,
                    "GLM_ENDPOINT_JOB": self.endpoint_job,
                    "OMP_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                    **extra_env,
                },
            ),
            constraints=[Constraint.create(key="cluster", op=ConstraintOp.EQ, value=self.cluster)],
            timeout=Duration.from_seconds(timeout_seconds),
            scheduling_timeout=Duration.from_seconds(600),
            max_retries_failure=0,
            max_retries_preemption=0,
            priority_band=job_pb2.PRIORITY_BAND_BATCH,
        )
        return str(job.job_id)
