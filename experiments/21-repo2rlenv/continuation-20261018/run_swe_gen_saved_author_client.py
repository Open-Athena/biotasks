"""Inference-only transport for a frozen native SWE-gen author invocation.

Repository builds/tests, author feedback and task fixes are excluded. The caller
transfers only the original candidate/source/profile and pinned author runtime.
"""

import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

import httpx
from iris.client.client import iris_ctx
from iris.cluster.types import JobName

from capture_author_process import capture
from preserve_author_output import preserve


def main():
    assert not os.environ.get("DAYTONA_API_KEY") and not os.environ.get("REPO2RLENV_REMOTE_WORKER")
    started = time.monotonic()
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    status = {"stage": "inference_only_saved_native_swe_gen_author", "status": "setup",
              "repository_builds_executed": False, "sandbox_provisioning": False,
              "preflight_generation_calls": 0, "maximum_native_author_calls": 1}
    try:
        manifest = json.loads(Path("manifest.json").read_text())
        assert manifest["prior_model_calls_for_selected_ids"] == 0
        assert manifest["model_calls_max_native_authoring"] == 1
        assert not manifest["task_specific_author_feedback_supplied"]
        assert not manifest["target_repository_execution"] and not manifest["Daytona_credentials_supplied"]
        for name, expected in manifest["files"].items():
            with Path(name).open("rb") as stream:
                assert Path(name).stat().st_size == expected["bytes"]
                assert hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]
        assert manifest["files"]["repo2rlenv-source.tar.gz"]["sha256"] == "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
        resolution = iris_ctx().client.resolver_for_job(JobName.from_string(os.environ["BIOTASKS21_GLM_RELAY_JOB"])).resolve("glm-5.3")
        assert resolution.endpoints
        endpoint = resolution.endpoints[0].url.rstrip("/")
        if not endpoint.endswith("/v1"):
            endpoint += "/v1"
        with httpx.Client(timeout=30) as client:
            response = client.get(endpoint + "/models", headers={"Authorization": "Bearer " + os.environ["BIOTASKS21_GLM_KEY"]})
            response.raise_for_status()
            assert any(x.get("id") == "glm-5.3" for x in response.json().get("data", []))
        status["models_http_status"] = 200
        with tarfile.open("repo2rlenv-source.tar.gz") as archive:
            archive.extractall("native-runtime", filter="data")
        roots = list(Path("native-runtime").iterdir())
        assert len(roots) == 1
        runtime = roots[0]
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        env.update(UV_PROJECT_ENVIRONMENT=str(runtime.resolve() / ".venv"), BIOTASKS21_GLM_ENDPOINT=endpoint)
        subprocess.run(["uv", "sync", "--frozen", "--no-dev", "--extra", "mutation", "--python", "3.12.3", "--project", str(runtime)], env=env, check=True, timeout=600)
        remaining = int(6900 - (time.monotonic() - started))
        assert remaining >= 1200
        command = [str(runtime / ".venv/bin/python"), "author_swe_gen_saved.py", "--candidate", "candidate.json", "--source", "frozen-source.json", "--profile", "profile.json", "--adaptation", "glm-generation-adaptation.json", "--output", "author-output"]
        status["status"] = "authoring"
        (output / "wrapper-status.json").write_text(json.dumps(status, indent=2) + "\n")
        code = capture(command, source=Path("author-output"), output=output / "child", timeout=remaining, env=env, maximum_bytes=64 * 1024**2)
        status.update(status="completed" if code == 0 else "failed", child_exit_code=code)
        return code
    except Exception as exc:
        status.update(status="setup_or_authoring_failed", error_type=type(exc).__name__)
        return 1
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "wrapper-status.json").write_text(json.dumps(status, indent=2) + "\n")
        if Path("author-output").is_dir() and not (output / "child/author-evidence.tar.gz").exists():
            preserve(Path("author-output"), output / "wrapper-fallback", max_bytes=64 * 1024**2)


if __name__ == "__main__":
    raise SystemExit(main())
