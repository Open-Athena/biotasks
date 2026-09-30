"""Keep the purposive panel distinct while measuring which misses depth alone recovers."""

import csv
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
inputs = [HERE.parent / "2026-09-30-discovery-gaps/audit.json", HERE / "rankings.csv"]
audit = json.loads(inputs[0].read_text())
by_source = {}
with inputs[1].open() as f:
    for r in csv.DictReader(f):
        by_source.setdefault(r["source_id"], {})[r["ranking"]] = int(r["rank"])
records = [
    dict(
        canonical=r["canonical"],
        in_original_github_pool=r["in_saved_github_pool"],
        top200=r["selected_ranks"],
        top300=by_source.get("github:" + r["canonical"].lower(), {}),
    )
    for r in audit["records"]
]
result = dict(
    checkpoint=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    input_sha256={
        str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
    },
    absent_top200=sum(not r["top200"] for r in records),
    absent_top300=sum(not r["top300"] for r in records),
    newly_selected=[r for r in records if not r["top200"] and r["top300"]],
    records=records,
)
(HERE / "gap-crosswalk.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    "Purposive panel absent from merged union:",
    result["absent_top200"],
    "at 200;",
    result["absent_top300"],
    "at 300. Not an unbiased recall estimate.",
)
