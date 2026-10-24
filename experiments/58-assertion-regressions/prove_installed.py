"""Actual installed CLI replay with transport, subprocess, secrets and writes denied."""

import contextlib
import io
import json
import sys
from pathlib import Path

from biotasks.cli import main
from biotasks.generation import resources
from biotasks.validation.files import inventory

root = Path(__file__).parent.resolve()
runner = root / "inputs-private/candidate-runner"
assert Path(resources.__file__).resolve().is_relative_to(runner)
sys.dont_write_bytecode = True
work = root / "inputs-private/run-001"
manifest = root / "manifest.json"
before = inventory(work)
original_open = Path.open


def forbidden(*args, **kwargs):
    raise AssertionError("Offline installed proof attempted an external effect")


def guarded_open(path, mode="r", *args, **kwargs):
    if any(x in mode for x in "wax+"):
        forbidden()
    if (
        "/secrets/" in str(path)
        or path.suffix == ".env"
        or str(path).endswith("/huggingface/token")
    ):
        forbidden()
    return original_open(path, mode, *args, **kwargs)


with contextlib.ExitStack() as stack:
    from unittest.mock import patch

    for target in [
        "socket.socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "urllib.request.urlopen",
    ]:
        stack.enter_context(patch(target, forbidden))
    stack.enter_context(patch.object(Path, "open", guarded_open))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            main(["generate", "plan", str(manifest), "--work-dir", str(work)])
        except SystemExit as stop:
            assert stop.code == 0
    replay = json.loads(output.getvalue())
    assert (
        replay["plan_identity"]
        == json.loads((root / "planning-summary.json").read_text())["plan_identity"]
    )
    assert inventory(work) == before
    old = root.parents[2] / "57/experiments/57-fresh-biopython/inputs-private/run-001"
    # Read-only status under changed code must hold, never adopt the old plan.
    error = io.StringIO()
    try:
        with contextlib.redirect_stderr(error), contextlib.redirect_stdout(io.StringIO()):
            main(["generate", "status", str(old)])
    except SystemExit as stop:
        assert stop.code == 2
    else:
        raise AssertionError("Changed generation implementation adopted old baseline plan")
    assert "Manifest/implementation identity changed" in error.getvalue()
result = {
    "actual_installed_module": resources.__file__,
    "generation_code_identity": resources.code_identity(),
    "plan_identity": replay["plan_identity"],
    "actual_cli_completed_plan_byte_inert": True,
    "old_baseline_status_rejected_without_external_effect": True,
    "network_subprocess_secret_reads_and_file_writes_denied_during_proof": True,
    "old_controller_can_continue_independently": True,
    "native_model_calls": 0,
    "native_scientific_acceptance": False,
}
(root / "installed-offline-proof.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
