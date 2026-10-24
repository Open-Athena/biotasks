"""Read-only, hash-bound source/state assessment; never executes saved commands."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKTREES = ROOT.parents[2]
PREDECESSOR = WORKTREES / "45/experiments/45-generation-handoff"
PACKAGE = WORKTREES / "31/experiments/31-historical-builds"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = PACKAGE / "package-acquisition.json"
    assert sha(manifest) == "5581e3126d5053450e2266ce0b504a0294197af5619ed69e187ca2311f605daf"
    acquisition = read(manifest)
    source_names = {
        "src/repo2rlenv/bootstrap/agent.py": ["run_agent_loop"],
        "src/repo2rlenv/bootstrap/runner.py": ["_verify_committed_image"],
        "src/repo2rlenv/registry/integration.py": [
            "_build_clean_recipe",
            "_load_bootstrap_recipe",
        ],
    }
    sources = []
    for name, functions in source_names.items():
        path = PACKAGE / "inputs-private/upstream-package" / name
        row = next(r for r in acquisition["files"] if r["path"] == name)
        assert sha(path) == row["sha256"] and path.stat().st_size == row["bytes"]
        nodes = {
            n.name: n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)
        }
        sources.append(
            {
                **row,
                "functions": {
                    f: {"start": nodes[f].lineno, "end": nodes[f].end_lineno} for f in functions
                },
            }
        )
    generation = PREDECESSOR / "inputs-private/generation-002/runs/generation"
    accepted = read(generation / "readback.json")
    directory = generation / "generation-source"
    # Reverify every member, not just the few values selected for the narrative.
    actual_paths = sorted(
        p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()
    )
    assert actual_paths == sorted(r["path"] for r in accepted["source_members"])
    for row in accepted["source_members"]:
        path = directory / row["path"]
        assert not path.is_symlink()
        assert sha(path) == row["sha256"] and path.stat().st_size == row["bytes"]
        assert path.stat().st_mode & 0o777 == row["mode"]
    cache = directory / "upstream/workspace/bootstrap/opencobra__cobrapy/a9c5ced29670__74ba7084"
    saved = read(cache / "bootstrap.json")
    turns = [json.loads(line) for line in (cache / "transcript.jsonl").read_text().splitlines()]
    apt = [
        {
            "step": v["step"],
            "action": v["action"],
            "input": v["input"],
            "observation": v["observation"],
        }
        for v in turns
        if v["action"] == "BASH" and "apt-get" in v["input"]
    ]
    result = {
        "source_revision": acquisition["revision"],
        "predecessor_evidence_commit": "7759bb06",
        "source_manifest_sha256": sha(manifest),
        "sources": sources,
        "generation_readback_sha256": sha(generation / "readback.json"),
        "generation_receipt": read(generation / "publication.json")["prefix"],
        "source_members_reverified": len(accepted["source_members"]),
        "bootstrap_sha256": sha(cache / "bootstrap.json"),
        "transcript_sha256": sha(cache / "transcript.jsonl"),
        "recorded_apt_actions": apt,
        "saved_rebuild_cmds": saved["rebuild_cmds"],
        "saved_test_cmds": saved["test_cmds"],
        "smoke_passed": saved["smoke_passed"],
        "verify_passed": saved["verify_passed"],
        "verify_detail": saved["verify_detail"],
        "transcript_rows": len(turns),
        "invalid_actions": sum(v["action"] == "INVALID" for v in turns),
        "provider_calls": accepted["model_billing"]["calls"],
        "billing_note": "Successful SAVE_SETUP returns without appending a transcript turn; transcript length is not provider call count.",
        "new_model_calls": 0,
        "new_remote_jobs": 0,
        "upstream_or_task_modified": False,
    }
    (ROOT / "source-assessment.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "source_members_reverified",
                    "invalid_actions",
                    "new_model_calls",
                    "new_remote_jobs",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
