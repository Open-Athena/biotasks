"""Check the retained experiment evidence without executing target code."""

import ast
import datetime
import hashlib
import json
import math
import resource
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def main():
    started = datetime.datetime.now(datetime.timezone.utc)
    scripts = list(ROOT.glob("*.py"))
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    cohort = json.loads((ROOT / "execution-cohorts-v2.json").read_text())["cohorts"]
    for row in cohort:
        assert digest(ROOT / row["diff_path"]) == row["diff_sha256"]
    frozen = json.loads((ROOT / "heldout-campaign.json").read_text())
    for name, expected in frozen["code_sha256"].items():
        assert digest(ROOT / name) == expected, name
    recovery = json.loads((ROOT / "recovery-v3-campaign.json").read_text())
    assert digest(ROOT / "run_campaign_capable.py") == recovery["launcher_sha256"]
    for name, expected in recovery["input_sha256"].items():
        assert digest(ROOT / name) == expected, name
    checked = 0
    for hashes_path in ROOT.glob("evidence/**/archive-file-hashes.json"):
        hashes = json.loads(hashes_path.read_text())
        if isinstance(hashes, list):
            hashes = {row["name"]: row["sha256"] for row in hashes}
        for name, expected in hashes.items():
            public_file = hashes_path.parent / name
            if public_file.is_file():
                assert digest(public_file) == expected, str(public_file)
                checked += 1
    failure = ROOT / "evidence/heldout-recovery-v3/psychopy"
    hashes = json.loads((failure / "archive-file-hashes.json").read_text())
    assert digest(failure / "bootstrap-failure.json") == hashes["exec-002.json"]
    costs = json.loads((ROOT / "evidence/cost-summary.json").read_text())
    for run in costs["runs"]:
        receipt = json.loads((ROOT / run["receipt"]).read_text())
        assert run["allocated_cpu_hours"] == receipt["allocated_cpu_hours"]
    summed = sum(run["allocated_cpu_hours"] for run in costs["runs"])
    summed += json.loads((ROOT / "evidence/probe-costs.json").read_text())["allocated_cpu_hours"]
    assert math.isclose(summed, costs["total_recorded_allocated_cpu_hours"])
    outcomes = json.loads((ROOT / "evidence/final-outcomes.json").read_text())
    qualified = sum(
        bool(row.get("export", {}).get("controls_passed"))
        for path in ROOT.glob("evidence/heldout-recovery-v3/*/development-result.json")
        for row in json.loads(path.read_text())["results"]
    )
    assert qualified == outcomes["denominators"]["qualified_technical_candidates"]
    lifecycle = json.loads((ROOT / "evidence/final-lifecycle.json").read_text())
    assert all(row["terminal"] for row in lifecycle["jobs"])
    ended = datetime.datetime.now(datetime.timezone.utc)
    result = {
        "started_at": started.isoformat(), "finished_at": ended.isoformat(),
        "elapsed_seconds": (ended - started).total_seconds(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "exit_status": 0, "syntax_checked_scripts": len(scripts),
        "cohort_patch_hashes_checked": len(cohort),
        "retained_archive_member_hashes_checked": checked,
        "frozen_worker_hashes_unchanged": True,
        "cost_and_outcome_consistency": True,
        "lifecycle_snapshot_all_terminal": True,
        "target_code_executed_by_this_check": False,
        "script_sha256": digest(Path(__file__)),
    }
    (ROOT / "evidence/final-evidence-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
