"""Read completed original ledgers; never run science, models or providers."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
manifest_bytes = (args.archive / "sealed-manifest.json").read_bytes()
manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
readback = json.loads((args.archive / "independent-readback.json").read_text())
assert readback["all_files_download_verified"]
assert readback["source_manifest_sha256"] == manifest_sha
rows = {row["path"]: row for row in json.loads(manifest_bytes)["files"]}
root = args.archive / "files"


def original(name):
    raw = (root / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == rows[name]["sha256"]
    assert len(raw) == rows[name]["bytes"]
    return json.loads(raw)


pipeline = original("pipeline.json")
assert "finished" in pipeline
stages = {
    stage["name"]: round(stage["finished"] - stage["started"], 3)
    for stage in pipeline["stages"]
    if "finished" in stage
}
ledgers = []
for name in sorted(rows):
    if not name.endswith("requests.sqlite"):
        continue
    path = root / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == rows[name]["sha256"]
    assert path.stat().st_size == rows[name]["bytes"]
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        calls = [
            {"scope": scope, "state": state, "count": count}
            for scope, state, count in connection.execute(
                "SELECT scope, state, COUNT(*) FROM calls GROUP BY scope, state"
            )
        ]
        count = connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    finally:
        connection.close()
    ledgers.append({"path": name, "sha256": rows[name]["sha256"], "count": count, "calls": calls})

charges = [
    (name.split("/charges/", 1)[0], original(name))
    for name in rows
    if "/charges/" in name and name.endswith(".json")
]
author_operations = {(stage, charge["operation"]) for stage, charge in charges}
result = {
    "source_archive_manifest_sha256": manifest_sha,
    "pipeline_status": pipeline["status"],
    "source_id": (pipeline.get("source") or {}).get("id"),
    "elapsed_pipeline_seconds": round(pipeline["finished"] - pipeline["started"], 3),
    "stage_elapsed_seconds": stages,
    "stage_status": {stage["name"]: stage["status"] for stage in pipeline["stages"]},
    "accounted_model_request_attempts": sum(ledger["count"] for ledger in ledgers),
    "request_ledgers": ledgers,
    "author_provider_response_receipts": len(charges),
    "distinct_author_response_operations_within_stage": len(author_operations),
    "scope": "Durable client/gateway request claims, including tool-use turns and retained failed/uncertain attempts. These are not a fixed stage count or a monetary invoice. SDK internal network transmissions beyond the recorded boundary are not separately inferred.",
    "method": "Immutable read-only SQL queries against every hash/size-verified original requests.sqlite; distinct author provider response receipt identities are counted separately. Stage intervals include incomplete stages; interpret them with stage_status. No live run or model call.",
    "logical_quality_repair_allowances_used": int(
        bool(pipeline.get("quality_repair"))
        or any(name.endswith("/repair.json") for name in rows if name.startswith("grading/"))
    ),
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {
            key: result[key]
            for key in [
                "source_id",
                "elapsed_pipeline_seconds",
                "accounted_model_request_attempts",
                "author_provider_response_receipts",
            ]
        }
    )
)
