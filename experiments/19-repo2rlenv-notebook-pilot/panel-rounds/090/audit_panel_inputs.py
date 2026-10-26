"""Check original-source configurations against the frozen common policy."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--launch-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists()
panel_path = Path(__file__).with_name("development-panel.json")
panel = json.loads(panel_path.read_text())
baseline_raw = (args.launch_root / "185-payload/campaign-config.json").read_bytes()
baseline = json.loads(baseline_raw)
source_keys = {"seed_file", "notebook_file", "source_notices_file"}
records = []
for case in panel["cases"]:
    number = case["original_input_campaign"]
    raw = (args.launch_root / f"{number:03}-payload/campaign-config.json").read_bytes()
    config = json.loads(raw)
    differences = {
        key
        for key in baseline.keys() | config.keys()
        if key != "campaign" and baseline.get(key) != config.get(key)
    }
    assert differences <= source_keys
    assert config["task_policy"] == baseline["task_policy"]
    records.append(
        {
            "source_id": case["source_id"],
            "original_input_campaign": number,
            "original_configuration_sha256": hashlib.sha256(raw).hexdigest(),
            "different_top_level_keys": sorted(differences),
            "task_policy_identical": True,
            "all_other_model_time_repair_and_execution_fields_identical": True,
        }
    )
result = {
    "observed_at": datetime.now(UTC).isoformat(),
    "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "panel_sha256": hashlib.sha256(panel_path.read_bytes()).hexdigest(),
    "baseline_configuration_sha256": hashlib.sha256(baseline_raw).hexdigest(),
    "cases": records,
    "new_jobs_or_model_calls": 0,
    "scientific_execution_or_acceptance_claimed": False,
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"cases": len(records), "same_execution_policy": True}))
