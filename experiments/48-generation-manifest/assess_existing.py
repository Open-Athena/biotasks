"""Read-only source inventory for reuse decisions, not runtime validation."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKTREES = ROOT.parents[2]
BASE = WORKTREES.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def own_sources(repository, names):
    commit = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    result = []
    for name in names:
        raw = (repository / name).read_bytes()
        expected = subprocess.check_output(
            ["git", "-C", str(repository), "show", commit + ":" + name]
        )
        assert raw == expected
        result.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
    return {"commit": commit, "files": result}


def main():
    package = WORKTREES / "31/experiments/31-historical-builds"
    acquisition = package / "package-acquisition.json"
    assert (
        sha(acquisition.read_bytes())
        == "5581e3126d5053450e2266ce0b504a0294197af5619ed69e187ca2311f605daf"
    )
    manifest = json.loads(acquisition.read_text())
    native_names = [
        "src/repo2rlenv/cli.py",
        "src/repo2rlenv/config.py",
        "src/repo2rlenv/tasksmith/batch.py",
        "src/repo2rlenv/tasksmith/runner.py",
        "src/repo2rlenv/tasksmith/native_stages.py",
    ]
    native = []
    for name in native_names:
        row = next(v for v in manifest["files"] if v["path"] == name)
        raw = (package / "inputs-private/upstream-package" / name).read_bytes()
        assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]
        native.append(row)
    previous = own_sources(
        WORKTREES / "45",
        [
            "experiments/45-generation-handoff/" + n
            for n in (
                "run_generation.py",
                "generation_entry.py",
                "generation_pipeline.py",
                "generation_worker.py",
                "generation_client.py",
                "model_budget.py",
                "handoff.py",
                "finish_generation.py",
            )
        ],
    )
    historical = own_sources(
        BASE,
        [
            "experiments/28-catalogued-fields/run_generation.py",
            "experiments/28-catalogued-fields/supervisor.py",
            "experiments/28-catalogued-fields/history-wide/run_history.py",
        ],
    )
    validator = own_sources(
        WORKTREES / "pipeline44-final",
        [
            "src/biotasks/validation/planning.py",
            "src/biotasks/validation/controller.py",
            "src/biotasks/validation/journal.py",
            "src/biotasks/validation/preservation.py",
            "docs/validation.md",
        ],
    )
    result = {
        "kind": "Source-only assessment; source hashes are verified, reuse conclusions are interface inferences rather than executed campaigns",
        "upstream_revision": manifest["revision"],
        "native_sources": native,
        "reference_sources": previous,
        "historical_orchestration": historical,
        "validator_component": validator,
        "reuse": [
            "Official one-config native generation and exact candidate/settings checks",
            "Isolated trusted credential delivery, original observers and conservative model admission",
            "Data-driven validation plans, seven-stage intent/evidence lifecycle and owned cleanup",
            "Historical explicit PR backlog, source identities and actual-cost accounting",
        ],
        "remaining_reference_specific_inputs": [
            "ROOT/proposed-native-config.json and ROOT/reference-candidates.json",
            "Planner requires exactly one candidate even though runtime compares a descriptor list",
            "Planner loads one fixed Cobrapy notice directory and writes its publication review",
            "Reference connector obtains its source/dependency template from one historical config",
        ],
        "not_reused_without_scope_change": "Tasksmith batch has a separate author/design/quality workflow; no such model calls are authorized by this assessment",
        "new_model_calls": 0,
        "new_remote_jobs": 0,
        "runtime_admitted": False,
        "pending_gate": "Finish47 accounting/archive/readback/cleanup before any later native admission",
    }
    (ROOT / "existing-interface-assessment.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "native_files": len(native),
            "reference_files": len(previous["files"]),
            "validator_files": len(validator["files"]),
            "new_calls": 0,
            "new_jobs": 0,
        }
    )


if __name__ == "__main__":
    main()
