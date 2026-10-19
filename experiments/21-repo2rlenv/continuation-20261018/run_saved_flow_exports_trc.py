"""Finish frozen SWE-Flow export/control stages without authoring or task edits."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from capture_author_process import capture


def verify(path, expected):
    with path.open("rb") as stream:
        assert path.stat().st_size == expected["bytes"]
        assert hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]


def main():
    started = time.monotonic()
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path("manifest.json").read_text())
    status = {
        "stage": "saved_native_flow_export_controls_not_admission",
        "model_calls": 0,
        "new_source_candidates": 0,
        "task_specific_fixes": 0,
        "records": [],
    }
    try:
        assert manifest["maximum_cases"] == len(manifest["cases"]) <= 3
        for filename, expected in manifest["files"].items():
            verify(Path(filename), expected)
        assert manifest["files"]["repo2rlenv-source.tar.gz"]["sha256"] == (
            "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
        )
        with tarfile.open("repo2rlenv-source.tar.gz") as archive:
            archive.extractall("native-runtime", filter="data")
        roots = list(Path("native-runtime").iterdir())
        assert len(roots) == 1
        runtime = roots[0]
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        # This controller receives no inference credential and makes no model call.
        assert not env.get("OPENAI_API_KEY") and not env.get("GLM_BULK_TOKEN")
        env["UV_PROJECT_ENVIRONMENT"] = str(runtime.resolve() / ".venv")
        subprocess.run(
            ["uv", "sync", "--frozen", "--no-dev", "--extra", "harbor", "--extra", "daytona", "--extra", "mutation", "--python", "3.12.3", "--project", str(runtime)],
            env=env, check=True, timeout=600,
        )
        python = str(runtime / ".venv/bin/python")
        for case in manifest["cases"]:
            remaining = int(6900 - (time.monotonic() - started))
            if remaining < 900:
                status["deadline_prevented_remaining_cases"] = True
                break
            name = case["name"]
            campaign = Path("flow-output") / name
            command = [python, "run_smith_controls.py", "--campaign", str(campaign), "--worker-name", os.environ["BIOTASKS21_WORKER_NAME"] + "-" + name, "--source-archive", "repo2rlenv-source.tar.gz", "--stage", "flow-controls", "--generation-archive", case["generation"], "--issues", case["issues"], "--config", case["profile"]]
            child_env = dict(env, BIOTASKS21_CONTROLLER_DEADLINE=str(remaining))
            row = {"name": name, "candidate_id": case["candidate_id"], "status": "running"}
            status["records"].append(row)
            (output / "flow-stage-summary.json").write_text(json.dumps(status, indent=2) + "\n")
            code = capture(command, source=campaign, output=output / name, timeout=remaining + 180, env=child_env, maximum_bytes=200 * 1024**2)
            row.update(status="controller_completed" if code == 0 else "controller_failed", controller_exit_code=code)
            result = campaign / "result.json"
            if result.exists():
                row["controller_result"] = json.loads(result.read_text())
            row["workers"] = [json.loads(file.read_text()) for file in (campaign / "workers").glob("*.json")]
            native = campaign / "native-evidence.tar.gz"
            if native.exists():
                with native.open("rb") as stream:
                    row["native_archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
                row["native_archive_bytes"] = native.stat().st_size
                with tarfile.open(native, "r|gz") as archive:
                    for member in archive:
                        if member.name == "native/validation/summary.json":
                            assert member.isfile() and member.size < 1024**2
                            row["native_summary"] = json.loads(archive.extractfile(member).read())
                            break
        status["status"] = "finished_recorded_stages"
        return 0
    except Exception as exc:
        status.update(status="setup_or_controller_failed", error_type=type(exc).__name__)
        return 1
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "flow-stage-summary.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
