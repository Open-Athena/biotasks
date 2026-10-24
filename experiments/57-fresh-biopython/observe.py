"""Observe the original fixed generation handle; never submit or repair."""

import json
from datetime import UTC, datetime
from pathlib import Path

from biotasks.generation import generation_bridge, run_generation
from biotasks.validation.files import require, sha

root = Path(__file__).parent.resolve()
work = root / "inputs-private/run-001/biopython"
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
    {"action": "observe", "group": plan["group"]},
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
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
(root / ("observation-" + stamp + ".json")).write_text(json.dumps(value, indent=2) + "\n")
print(json.dumps(value, indent=2))
