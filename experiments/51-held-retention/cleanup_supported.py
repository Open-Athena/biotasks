"""Remove only disposable supported-check fixtures after retaining code/logs/wheel."""

import shutil
from pathlib import Path

from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json

root = Path(__file__).resolve().parent
original = root.parents[2] / "47/experiments/47-bootstrap-recipe-state/inputs-private/comparison-001/validation"
before = json_sha(inventory(original))
ledger = Path(read_json(original / "plan.json")["budget_ledger"])
budget_before = sha(ledger)
artifacts = read_json(root / "installed-source-receipt.json")["artifacts"]
for row in artifacts:
    path = Path(row["path"])
    require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], "Built artifact changed")
require(read_json(root / "installed-offline-proof.json")["actual_installed_cli_plan_and_run_invoked"] is True, "Installed CLI proof missing")
removed = []
for name in ("supported-002", "supported-003"):
    directory = root / "local-scratch" / name
    require(directory.is_dir() and not directory.is_symlink(), "Unexpected scratch root")
    files = size = links = 0
    for path in directory.rglob("*"):
        if path.is_symlink():
            links += 1
        elif path.is_file():
            files += 1
            size += path.stat().st_size
    removed.append({"path": str(directory), "regular_files": files, "logical_bytes": size, "pytest_alias_symlinks": links})
    shutil.rmtree(directory)
(root / "local-scratch").rmdir()
require(json_sha(inventory(original)) == before and sha(ledger) == budget_before, "Original evidence/budget changed")
write_json(root / "installed-cleanup.json", {"removed_disposable_tests": removed, "retained_artifact_hashes_verified": True, "original_source_and_budget_unchanged": True, "source_inventory_sha256": before, "budget_sha256": budget_before, "task_owned_tmp_paths": [], "retained": ["inputs-private/candidate-artifacts", "inputs-private/candidate-runner", "inputs-private/archived-001", "inputs-private/installed-001"], "cleanup_condition": "Retain cited proofs and exact candidate runtime while follow-up native regression depends on them; originals and HF snapshots retained while cited"})
print({"removed_regular_files": sum(row["regular_files"] for row in removed), "removed_logical_bytes": sum(row["logical_bytes"] for row in removed), "owned_tmp_paths": []})
