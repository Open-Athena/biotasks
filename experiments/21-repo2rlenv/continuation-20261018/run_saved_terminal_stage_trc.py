"""Fixed TRC setup, transport check and native continuation of one saved design."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

from package_provider_task import unpack
from preserve_author_output import preserve


def main():
    started = time.monotonic()
    capture = Path(os.environ["IRIS_OUTPUT_DIR"])
    capture.mkdir(parents=True, exist_ok=True)
    status = {"stage": "saved_design_native_stage_wrapper", "manual_output_fixes": 0,
              "external_task_feedback": False, "new_design_calls": 0}
    try:
        recipe = os.environ["BIOTASKS21_SAVED_RECIPE"]
        assert recipe in ("seta_seed2synth", "seta_evol")
        inputs = json.loads(Path("dispatch-inputs.json").read_text())
        assert inputs["recipe"] == recipe
        for name, record in inputs["files"].items():
            data = Path(name).read_bytes()
            assert len(data) == record["bytes"] and hashlib.sha256(data).hexdigest() == record["sha256"]
        if recipe == "seta_evol":
            unpack(Path("parent-bundle.tar.gz"), Path("parent-bundle-manifest.json"), Path("."))
            Path("task").rename("parent")
        source = Path("repo2rlenv-source.tar.gz")
        with source.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
        base = os.environ["BIOTASKS21_INFERENCE_CLIENT_URL"].rstrip("/")
        application = os.environ["BIOTASKS21_GENERATION_CLIENT_TOKEN"]
        body = json.dumps({"model": "glm-5.3", "max_tokens": 131072,
                           "chat_template_kwargs": {"reasoning_effort": "medium"},
                           "messages": [{"role": "user", "content": "Transport receipt only."}]}).encode()
        request = urllib.request.Request(base + "/v1/transport-check", data=body,
            headers={"Content-Type": "application/json", "X-Biotasks21-Inference-Token": application})
        with urllib.request.urlopen(request, timeout=30) as response:
            receipt = json.load(response)
        assert receipt["model_calls"] == 0 and receipt["request_sha256"] == hashlib.sha256(body).hexdigest()
        (capture / "transport-preflight.json").write_text(json.dumps(receipt, indent=2) + "\n")
        with tarfile.open(source) as archive:
            archive.extractall("native-runtime", filter="data")
        roots = list(Path("native-runtime").iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP="True")
        env.pop("VIRTUAL_ENV", None)
        env["UV_PROJECT_ENVIRONMENT"] = str(root.resolve() / ".venv")
        with (capture / "private-setup.log").open("w") as log:
            subprocess.run(["uv", "sync", "--frozen", "--no-dev", "--extra", "harbor", "--extra", "daytona",
                            "--python", "3.12.3", "--project", str(root)], env=env, stdout=log, stderr=log, check=True, timeout=600)
            subprocess.run(["uv", "build", "--wheel", "--project", str(root)], env=env,
                           stdout=log, stderr=log, check=True, timeout=300)
        wheels = list((root / "dist").glob("*.whl"))
        assert len(wheels) == 1
        remaining = int(os.environ["BIOTASKS21_TOTAL_DEADLINE_SEC"]) - int(time.monotonic() - started)
        if not 900 <= remaining <= 6900:
            raise TimeoutError("Insufficient fixed native generation window")
        env.update(REPO2RLENV_MODEL_WORKER="1", BIOTASKS21_GLM_ENDPOINT=base + "/v1",
                   BIOTASKS21_GLM_KEY=application, BIOTASKS21_CONTROLLER_DEADLINE=str(remaining))
        command = [str(root / ".venv/bin/python"), "run_saved_terminal_build.py", "--recipe", recipe,
            "--campaign", "author-output", "--source", "seeds.json" if recipe == "seta_seed2synth" else "parent",
            "--designs", "saved-designs.json", "--stage-proof", "saved-terminal-stage-reconciliation.json",
            "--wheel", str(wheels[0]), "--adaptation", "glm-generation-adaptation.json",
            "--run-id", os.environ["BIOTASKS21_SAVED_RUN_ID"], "--worker-name", os.environ["BIOTASKS21_WORKER_NAME"]]
        if recipe == "seta_evol":
            command.extend(["--parent-manifest", "parent-manifest.json"])
        with (capture / "private-controller.log").open("w") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=remaining + 240)
        status.update(child_exit_code=result.returncode, status="completed" if result.returncode == 0 else "native_pipeline_failed")
        return result.returncode
    except Exception as exc:
        status.update(status="setup_or_native_pipeline_failed", error_type=type(exc).__name__)
        return 1
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (capture / "wrapper-status.json").write_text(json.dumps(status, indent=2) + "\n")
        if Path("author-output").is_dir() and not (capture / "after-cleanup/author-evidence.tar.gz").exists():
            preserve(Path("author-output"), capture / "wrapper-fallback")


if __name__ == "__main__":
    raise SystemExit(main())
