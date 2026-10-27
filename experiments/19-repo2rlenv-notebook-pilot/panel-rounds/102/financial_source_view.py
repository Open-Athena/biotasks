"""Materialize a bounded immutable Git source view for an unchanged old auditor.

This does not checkout, execute, rewrite or relabel scientific artifacts. Its
manifest binds every copied file to an existing Git tree and all runtime hashes.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", required=True)
parser.add_argument("--destination", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[4]
prefix = "experiments/19-repo2rlenv-notebook-pilot/"
revision = subprocess.check_output(
    ["git", "rev-parse", "--verify", args.revision + "^{commit}"], cwd=repo, text=True
).strip()
identity_path = prefix + "panel-rounds/101/runtime-identity.json"
runtime = json.loads(
    subprocess.check_output(["git", "show", revision + ":" + identity_path], cwd=repo)
)["runtime_files"]
paths = [
    *runtime,
    prefix + "factory-checks",
    *(prefix + "panel-rounds/" + value for value in ("070", "079", "100", "101")),
]
listing = subprocess.check_output(
    ["git", "ls-tree", "-r", "-l", "-z", revision, "--", *paths], cwd=repo
)
entries = {}
for record in listing.split(b"\0"):
    if not record:
        continue
    metadata, name = record.decode().split("\t", 1)
    mode, kind, blob, size = metadata.split()
    assert kind == "blob" and mode in {"100644", "100755"}
    entries[name] = {"blob": blob, "bytes": int(size), "mode": int(mode, 8) & 0o777}
assert set(runtime) <= set(entries)
total = sum(row["bytes"] for row in entries.values())
assert not args.destination.exists() and not args.manifest.exists()
args.destination.parent.mkdir(parents=True, exist_ok=True)
assert shutil.disk_usage(args.destination.parent).free - total >= 2 * 1024**3
args.destination.mkdir(mode=0o700)
process = subprocess.Popen(
    ["git", "archive", "--format=tar", revision, "--", *paths], cwd=repo, stdout=subprocess.PIPE
)
assert process.stdout is not None
seen = set()
with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
    for item in archive:
        relative = PurePosixPath(item.name)
        assert not relative.is_absolute() and ".." not in relative.parts
        target = args.destination / item.name
        if item.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        assert item.isfile() and item.name in entries and item.name not in seen
        row = entries[item.name]
        assert item.size == row["bytes"]
        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive.extractfile(item)
        assert source is not None
        with target.open("xb") as stream:
            shutil.copyfileobj(source, stream, length=128 * 1024)
        target.chmod(row["mode"])
        with target.open("rb") as stream:
            row["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        seen.add(item.name)
assert process.wait() == 0 and seen == set(entries)
assert all(entries[name]["sha256"] == value for name, value in runtime.items())
proof = {
    "revision": revision,
    "files": entries,
    "file_count": len(entries),
    "bytes": total,
    "runtime_files": len(runtime),
    "all_runtime_hashes_verified": True,
    "scientific_execution": False,
    "original_artifacts_changed": False,
    "new_models_or_resources": 0,
}
args.manifest.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps({key: value for key, value in proof.items() if key != "files"}))
