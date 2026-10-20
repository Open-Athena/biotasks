"""Use existing reserved TRC CPU for native source selection only."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path


def main():
    started = time.monotonic()
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path("manifest.json").read_text())
    for name, expected in manifest["files"].items():
        with Path(name).open("rb") as stream:
            assert Path(name).stat().st_size == expected["bytes"]
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]
    assert not os.environ.get("GLM_BULK_TOKEN") and not os.environ.get("DAYTONA_API_KEY")
    record = {"stage": "TRC_native_history_source_selection", "model_calls": 0,
              "Daytona_credentials_supplied": False, "target_code_execution": False}
    try:
        with tarfile.open("repo2rlenv-source.tar.gz") as archive:
            archive.extractall("native-runtime", filter="data")
        roots = list(Path("native-runtime").iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        env["UV_PROJECT_ENVIRONMENT"] = str(root.resolve() / ".venv")
        env["BIOTASKS21_TRC_SOURCE_INTAKE"] = "1"
        subprocess.run(["uv", "sync", "--frozen", "--no-dev", "--extra", "mutation",
                        "--python", "3.12.3", "--project", str(root)],
                       env=env, check=True, timeout=600)
        command = [str(root / ".venv/bin/python"), "prepare_frozen_history_sources.py",
                   "--inputs", ".", "--output", str(output / "native")]
        with (output / "native-process.log").open("w") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=2400)
        record["returncode"] = result.returncode
        record["status"] = "completed" if result.returncode == 0 else "native_selection_failed"
        return result.returncode
    except Exception as exc:
        record.update(status="setup_or_selection_failed", error_type=type(exc).__name__)
        return 1
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "wrapper-status.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
