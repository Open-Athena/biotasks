"""Observe the original fixed generation handle; never submit or repair."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from biotasks.generation import generation_bridge, run_generation
from biotasks.validation import preservation
from biotasks.validation.files import require, sha

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()
root = Path(__file__).parent.resolve()
work = root / "inputs-private/run-001/dendropy"
plan = run_generation.verify(work)
receipt = work / "runs/generation/submission.json"
require(
    receipt.is_file(),
    "No original submission receipt yet; observe the live controller, do not submit",
)
job_id = "/exedev/" + plan["group"]["run_id"]
require(json.loads(receipt.read_text())["job_id"] == job_id, "Unexpected original handle")
profile = generation_bridge.call(
    plan["backend"], {"action": "fingerprint"}, root / "inputs-private/observer-profile.log"
)
require(profile == plan["client_profile"], "Observer SDK source changed")
require(
    sha(Path(plan["backend"]["config"])) == plan["backend_config_sha256"],
    "Observer backend config changed",
)
result = generation_bridge.call(
    plan["backend"],
    {"action": "logs" if args.logs else "observe", "group": plan["group"]},
    root / "inputs-private/observer-status.log",
)
value = {
    "observed_utc": datetime.now(UTC).isoformat(),
    "original_job": result,
    "read_only": True,
    "observer_new_model_calls": 0,
    "job_model_usage": "Not measured by job status; await original recorded billing",
    "plan_identity": plan["plan_identity"],
}
raw = json.dumps(value).encode()
require(len(raw) <= 512 * 1024, "Bounded observation exceeded")
preservation.inspect(raw, "original-job-observation.json")
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
target = (
    root
    / ("inputs-private" if args.logs else ".")
    / (("logs-" if args.logs else "observation-") + stamp + ".json")
)
target.write_text(json.dumps(value, indent=2) + "\n")
print(
    json.dumps(
        {
            "path": str(target),
            "rows": len(result.get("logs", [])),
            "read_only": True,
            "observer_new_model_calls": 0,
        }
    )
    if args.logs
    else json.dumps(value, indent=2)
)
