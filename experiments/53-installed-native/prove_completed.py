"""Reinvoke the completed installed CLI with transport and credential reads blocked."""

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json

from biotasks.cli import main

root = Path(__file__).resolve().parent
work = root / "inputs-private/run-001"
expected = json.loads((root / "inputs-private/controller-output.log").read_text())
require(expected["state"] == "workflow_complete", "Original workflow not complete")
manifest = read_json(root / "manifest.json")
ledger = Path(manifest["budget_ledger"])
before, cost = inventory(work), sha(ledger)


def audit(event, values):
    if event in {
        "socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
    }:
        raise AssertionError("Completed replay must not use transport")
    if event == "open" and isinstance(values[0], (str, bytes)):
        if any(
            part in str(values[0])
            for part in ("/.codex/secrets/", "/.config/coreweave/", "/.cache/huggingface/token")
        ):
            raise AssertionError("Completed replay must not read credentials")


sys.addaudithook(audit)
capture = StringIO()
with redirect_stdout(capture):
    try:
        main(["generate", "run", str(work), "--allow-generation", "--allow-validation", "--once"])
    except SystemExit as error:
        require(error.code in (0, None), "Completed CLI failed")
actual = json.loads(capture.getvalue())
require(actual == expected, "Completed result changed")
require(inventory(work) == before and sha(ledger) == cost, "Completed evidence/accounting changed")
write_json(
    root / "completed-replay-proof.json",
    {
        "result": actual,
        "work_inventory_sha256": json_sha(before),
        "work_files": len(before),
        "budget_sha256": cost,
        "actual_installed_cli_invoked": True,
        "transport_and_credential_reads_forbidden": True,
        "completed_replay_byte_inert": True,
        "new_model_native_jobs_or_calls": 0,
        "source_checkpoint": "88a02827b5b0a43d53fc9dbc6eb434ddbc0c56d0",
        "scientific_acceptance": False,
    },
)
print(
    json.dumps(
        {
            "state": actual["state"],
            "byte_inert": True,
            "new_calls_or_jobs": 0,
            "budget_sha256": cost,
        },
        indent=2,
    )
)
