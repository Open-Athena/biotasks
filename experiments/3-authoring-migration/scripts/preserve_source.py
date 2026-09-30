"""One-off, offline import of the frozen authoring handoff. Never run workers."""

import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "experiments/3-authoring-migration"
SOURCE = Path("/home/exedev/.codex/worktrees/ddcd/marin")
PREFIX = "docs/experiments/bio-task-generation/"
REVISION = "37973a95c71d5e1d38bb15c238f1d40369255359"
INTEGRATION = "72008dd68247318a367a840a4f41e27fb15ff7e1"
BASE = "37271415c4c201ba9dbbda66c203caa4050744c3"


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args])


def metadata(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    if (STUDY / "migration.json").exists():
        raise SystemExit("Existing preservation manifest; refusing to overwrite.")
    assert git("rev-parse", "HEAD").decode().strip() == REVISION
    status = git("status", "--porcelain=v1", "--untracked-files=all").decode()
    assert not status, "Reconcile source changes before preservation"
    changed = {}
    for line in git("diff", "--name-status", "--no-renames", INTEGRATION, REVISION).decode().splitlines():
        change, path = line.split("\t")
        assert path.startswith(PREFIX) and "/01-discovery/" not in path
        changed[path] = change
    tracked = []
    for path in git("ls-tree", "-r", "--name-only", REVISION, PREFIX).decode().splitlines():
        data = git("show", f"{REVISION}:{path}")
        destination = STUDY / "baseline" / path.removeprefix(PREFIX)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        tracked.append({"source_path": path, "destination": str(destination.relative_to(ROOT)),
                        "change": changed.get(path, "unchanged-context"),
                        "disposition": "migrated-byte-identical", **metadata(data)})
    assert set(changed) <= {item["source_path"] for item in tracked}
    local_root = SOURCE / "artifacts/bio-task-generation"
    local = []
    for path in sorted(local_root.rglob("*")):
        if not path.is_file():
            continue
        assert not path.is_symlink()
        data = path.read_bytes()
        entry = {"path": str(path.relative_to(local_root)), **metadata(data),
                 "disposition": "retained-at-source-pending-archive-review"}
        if path.parent == local_root and path.suffix == ".py":
            destination = STUDY / "baseline/local-helpers" / (path.name + ".txt")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            entry.update(disposition="migrated-historical-helper-byte-identical",
                         destination=str(destination.relative_to(ROOT)))
        local.append(entry)
    observed = datetime.datetime.now(datetime.UTC).isoformat()
    manifest = {
        "schema_version": 1, "captured_at_utc": observed,
        "question": "Preserve and assess Marin authoring research for BioTasks issue #3",
        "source_repository": "https://github.com/marin-community/marin",
        "source_branch": "codex/bio-tasks-authoring", "source_revision": REVISION,
        "integration_revision": INTEGRATION, "destination_main_revision": BASE,
        "source_checkout": str(SOURCE), "source_worktree_status": status,
        "tracked_changed_paths": len(changed), "tracked_preserved_files": len(tracked),
        "path_policy": "Exact source subtree under baseline; historical links, commands and hashes unchanged. Adaptations are separate and recorded.",
        "drafting_time_local_additions": "Round-two/round-three and comparison changes committed by c97c2469120f91931fdec648714a755d20604b47; source clean at capture.",
        "tracked_files": tracked,
    }
    save_json(STUDY / "migration.json", manifest)
    save_json(STUDY / "runs/2026-09-30-migration/local-files.json", {
        "captured_at_utc": observed, "source_root": str(local_root),
        "files": local, "file_count": len(local), "total_bytes": sum(x["bytes"] for x in local),
        "retention": "Keep original source files until explicit durable archive disposition; do not delete on migration or issue closure.",
        "note": "This is an inventory, not a public upload allowlist. Raw logs and third-party cache terms need review.",
    })
    print(json.dumps({"changed_paths": len(changed), "preserved_files": len(tracked),
                      "preserved_bytes": sum(x["bytes"] for x in tracked),
                      "local_files": len(local), "local_bytes": sum(x["bytes"] for x in local)}))


if __name__ == "__main__":
    main()
