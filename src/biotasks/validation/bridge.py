"""Run the optional Iris client in its configured environment, not the task image."""

import json
import subprocess
from pathlib import Path
from typing import Any

from biotasks.validation.files import MAX_ARCHIVE, ValidationError, require

MARKER = "BIOTASKS_VALIDATION_RESULT="


def call(backend: dict[str, Any], request: dict[str, Any], log: Path) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    launcher = "import runpy,sys;sys.path.insert(0,sys.argv[1]);runpy.run_module('biotasks.validation.iris_client',run_name='__main__')"
    log.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [backend["python"], "-c", launcher, str(root)],
        input=json.dumps({**request, "backend": backend}),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    require(len(result.stdout) + len(result.stderr) <= MAX_ARCHIVE, "Backend output exceeds bound")
    log.write_text(result.stdout + "\n" + result.stderr)
    rows = [line[len(MARKER) :] for line in result.stdout.splitlines() if line.startswith(MARKER)]
    if result.returncode or len(rows) != 1:
        raise ValidationError(f"Iris client failed; inspect protected log {log}")
    value = json.loads(rows[0])
    require(isinstance(value, dict), "Invalid backend response")
    return value
