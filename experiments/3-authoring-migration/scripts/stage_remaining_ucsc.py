"""Stage the final three UCSC captures with original terms and provenance."""

import hashlib
import json
import shutil
import sys
from pathlib import Path


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


run = Path("experiments/3-authoring-migration/runs/2026-09-30-ucsc-remaining")
previous = json.loads((run.parent / "2026-09-30-ucsc-supplement/allowlist.json").read_text())
originals = previous["exclusions"]
assert len(originals) == 3
stage = Path(sys.argv[1])
stage.mkdir(parents=True, exist_ok=False)
for item in originals:
    path = Path(item["retained_root"]) / item["path"]
    assert not path.is_symlink()
    assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]
    target = stage / item["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
notices = [
    "licenses/kent.txt",
    "licenses/kent-utils.txt",
    "licenses/kent-liftover.txt",
    "licenses/kent-blat.txt",
    "provenance.json",
    "NOTICE.md",
]
for name in notices:
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
    assert expected[item["path"]] == {key: item[key] for key in ("path", "bytes", "sha256")}
inventory = {
    "source_root": str(stage.resolve()),
    "scope": "Final issue 3 migration supplement: three unchanged UCSC research captures with upstream notices and provenance. No relicensing, task release or scientific validation.",
    "files": files,
    "provenance": json.loads((run / "provenance.json").read_text()),
    "eligibility": {
        "decision": "User explicitly instructed public archival of the remaining three files after discussion of their terms. Preserve original terms; no new upstream permission or blanket MIT classification is claimed.",
        "original_files": len(originals),
        "original_bytes": sum(item["bytes"] for item in originals),
        "notices": notices,
    },
    "exclusions": [],
}
(run / "allowlist.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
print(
    json.dumps({"original_files": len(originals), "staged_files": len(files), "stage": str(stage)})
)
