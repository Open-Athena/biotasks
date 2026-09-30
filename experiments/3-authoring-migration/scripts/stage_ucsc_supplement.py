"""Stage three reviewed UCSC cache files with their exact upstream notices."""

import hashlib
import json
import shutil
import sys
from pathlib import Path


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


run = Path("experiments/3-authoring-migration/runs/2026-09-30-ucsc-supplement")
retained = json.loads((run.parent / "2026-09-30-worktree-retention/manifest.json").read_text())
source = Path(retained["retained_root"])
stage = Path(sys.argv[1])
stage.mkdir(parents=True, exist_ok=False)
selected = {
    "ucsc-README",
    "ucsc-src-utils-bedGraphToBigWig-bedGraphToBigWig.c",
    "ucsc-src-utils-bigWigAverageOverBed-bigWigAverageOverBed.c",
}
originals = [item for item in retained["files"] if Path(item["path"]).name in selected]
assert len(originals) == len(selected)
for item in originals:
    path = source / item["path"]
    assert not path.is_symlink()
    assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]
    target = stage / item["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
for name in ("licenses/kent.txt", "licenses/kent-utils.txt", "provenance.json", "NOTICE.md"):
    target = stage / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run / name, target)
files = [
    {"path": str(path.relative_to(stage)), "bytes": path.stat().st_size, "sha256": digest(path)}
    for path in sorted(stage.rglob("*"))
    if path.is_file()
]
expected = {item["path"]: item for item in files}
for item in originals:
    assert expected[item["path"]] == item
inventory = {
    "source_root": str(stage.resolve()),
    "scope": "Supplement to issue 3 migration: three unchanged UCSC review files and their license/provenance notices. No model calls, scientific validation or task release.",
    "files": files,
    "provenance": json.loads((run / "provenance.json").read_text()),
    "eligibility": {
        "review": "Original blanket UCSC exclusion corrected by file-specific license review. Preserve all notices; do not extend utilities MIT terms to liftOver or other directories.",
        "original_files": len(originals),
        "original_bytes": sum(item["bytes"] for item in originals),
        "licenses": ["licenses/kent.txt", "licenses/kent-utils.txt"],
    },
    "exclusions": [
        {
            **item,
            "disposition": "Verified private local copy outside managed worktrees; public redistribution scope unresolved, not asserted prohibited.",
            "retained_root": str(source),
        }
        for item in retained["files"]
        if Path(item["path"]).name not in selected
    ],
}
(run / "allowlist.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
print(
    json.dumps({"original_files": len(originals), "staged_files": len(files), "stage": str(stage)})
)
