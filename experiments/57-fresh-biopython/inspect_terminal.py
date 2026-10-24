"""Read-only early view of the original terminal archive; no journal or ledger writes.

Canonical controller archival, billing, publication and cleanup remain required.
The independent copy is source/hash checked and kept protected; no task repair.
"""

import gzip
import json
from pathlib import Path

import zstandard
from biotasks.generation.generation_pipeline import billing
from biotasks.generation.run_generation import verify
from biotasks.validation import collection, preservation
from biotasks.validation.archives import records
from biotasks.validation.files import require, sha

root = Path(__file__).parent.resolve()
work = root / "inputs-private/run-001/biopython"
plan = verify(work)
observation = json.loads((root / "observation-20261024T222947Z.json").read_text())
account = observation["original_job"]
require(
    account.get("terminal") is True and account["attempts"] == 1, "Need original terminal attempt"
)
require(account["job_id"] == "/exedev/" + plan["group"]["run_id"], "Wrong handle")
require(account["output_archive"]["size_bytes"] <= 2 * 1024**2, "Early inspection compressed bound")
directory = root / "inputs-private/terminal-inspection-001"
directory.mkdir(exist_ok=False)
raw = collection.download(account, directory, plan["backend"].get("gcloud", "gcloud"))
with raw.open("rb") as stream, zstandard.ZstdDecompressor().stream_reader(stream) as reader:
    require(len(reader.read(8 * 1024**2 + 1)) <= 8 * 1024**2, "Early inspection expanded bound")
submission = json.loads((work / "runs/generation/submission.json").read_text())
report, outer = collection.envelope(
    raw, submission, plan["group"]["payload_sha256"], "generate", plan["group"]["run_id"]
)
packed = outer.get("control-artifacts.tar.gz")
phase = {}
if packed:
    import io

    with gzip.GzipFile(fileobj=io.BytesIO(packed["data"])) as stream:
        require(len(stream.read(8 * 1024**2 + 1)) <= 8 * 1024**2, "Early nested expansion bound")
    phase = records(packed["data"], "tar.gz")
for name in [
    "native-generation.log",
    "native-observations/events.jsonl",
    "native-observations/billing.json",
]:
    if name in phase:
        preservation.inspect(phase[name]["data"], name)
        target = directory / Path(name).name
        target.write_bytes(phase[name]["data"])
events = [
    json.loads(x)
    for x in phase.get("native-observations/events.jsonl", {"data": b""})["data"].splitlines()
]
value = {
    "original_terminal_archive_sha256": sha(raw),
    "source_and_worker_envelope_verified": True,
    "primary_allocated_cpu_hours": account["allocated_cpu_hours"],
    "native_exit": report.get("native_exit"),
    "wrapper_stage": report.get("stage"),
    "billing_observed_not_reconciled": billing(phase, report),
    "native_decisions": [
        r
        for r in events
        if r.get("event")
        in ["native_decision", "validation_start", "validation_end", "validation_exception"]
    ],
    "raw_export_metadata_paths": sorted(
        n for n in phase if n.startswith("outputs/raw/") and n.endswith("/task.toml")
    ),
    "phase_members": [
        {"path": n, "sha256": r["sha256"], "bytes": r["bytes"]} for n, r in sorted(phase.items())
    ],
    "canonical_controller_journal_or_ledger_changed_by_inspector": False,
    "native_jobs_or_model_calls_started_by_inspector": 0,
    "scientific_acceptance": False,
    "canonical_retention_and_cleanup_pending": True,
}
preservation.inspect(json.dumps(value).encode(), "terminal-inspection-summary.json")
(root / "terminal-inspection-summary.json").write_text(json.dumps(value, indent=2) + "\n")
print(json.dumps({k: v for k, v in value.items() if k != "phase_members"}, indent=2))
