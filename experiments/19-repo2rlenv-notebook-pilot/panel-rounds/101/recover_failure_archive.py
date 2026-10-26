"""Verify a campaign's existing fallback snapshot and original root export.

Uses the submission-bound bootstrap's tested streaming restorer. No scientific
execution or reconstruction of an absent ordinary autonomous export seal.
"""

import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from rigging.filesystem.buckets import filesystem_for

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / "factory-checks/archive-recovery"))
from readback_cache import store  # noqa: E402

number = int(sys.argv[1])
assert 196 <= number <= 205
base = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
root = base / f"archives/{number:03}"
claim_raw = (base / f"launch/{number:03}-submission.json").read_bytes()
claim = json.loads(claim_raw)
prefix = (
    "s3://marin-us-east-02a/marin/evals/biotasks19/20261026-panel101/"
    f"biotasks19-autonomous-panel-{number:03}/"
)
cache = {}


def metadata(relative):
    fs, key = filesystem_for(prefix + relative)
    with fs.open(key, "rb", cache_type="none", block_size=1024 * 1024) as source:
        raw = source.read(8 * 1024 * 1024 + 1)
    assert len(raw) <= 8 * 1024 * 1024
    return raw


def save_original(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    assert not path.is_symlink()
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)
        path.chmod(0o600)


def retrieve(relative, destination, row):
    path = PurePosixPath(row["path"])
    assert not path.is_absolute() and ".." not in path.parts
    assert str(path) == row["path"] and str(path) != "."

    def stream():
        fs, key = filesystem_for(prefix + relative + row["path"])
        return fs.open(key, "rb", cache_type="none", block_size=1024 * 1024)

    return store(stream, destination / row["path"], row, cache)


transport = root / "snapshot-transport"
seal_raw = metadata("autonomous-snapshot/export-manifest.json")
seal = json.loads(seal_raw)
assert seal["download_checked"] is True
rows = {row["path"]: row for row in seal["files"]}
assert len(seal["files"]) == 2 and set(rows) == {"snapshot-files.json", "evidence.tar.gz"}
save_original(transport / "export-manifest.json", seal_raw)
retrieve("autonomous-snapshot/", transport, rows["snapshot-files.json"])
members = json.loads((transport / "snapshot-files.json").read_text())
assert members["source_quiescent"] is True
required = sum(row["bytes"] for row in members["files"]) + rows["evidence.tar.gz"]["bytes"]
assert shutil.disk_usage(root).free - required >= 2 * 1024**3, "Retain local disk headroom"
retrieve("autonomous-snapshot/", transport, rows["evidence.tar.gz"])

bootstrap = base / f"launch/{number:03}-payload/bootstrap.py"
bootstrap_sha = hashlib.sha256(bootstrap.read_bytes()).hexdigest()
assert bootstrap_sha == claim["inputs"]["files"]["bootstrap.py"]
spec = importlib.util.spec_from_file_location("original_campaign_bootstrap", bootstrap)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
restored = root / "snapshot-restored"
assert not restored.exists(), "Do not overwrite an earlier recovery"
snapshot = module.restore_snapshot(transport, restored)
assert snapshot["all_snapshot_files_hash_size_mode_verified"] is True

root_seal = metadata("export-manifest.json")
manifest = json.loads(root_seal)
assert manifest["download_checked"] is True
assert sum(row["bytes"] for row in manifest["files"]) <= 32 * 1024 * 1024
destination = root / "root-evidence"
save_original(destination / "sealed-root-manifest.json", root_seal)
assert len({row["path"] for row in manifest["files"]}) == len(manifest["files"])
for row in manifest["files"]:
    retrieve("", destination / "files", row)
root_readback = {
    "observed_at": datetime.now(UTC).isoformat(),
    "root_manifest_sha256": hashlib.sha256(root_seal).hexdigest(),
    "all_manifest_files_hash_size_mode_verified": True,
    "file_count": len(manifest["files"]),
    "bytes": sum(row["bytes"] for row in manifest["files"]),
    "source_full_snapshot_manifest_sha256": snapshot["source_manifest_sha256"],
    "files": manifest["files"],
    "scope": "Complete original root export, linked to the separately verified fallback snapshot.",
}
save_original(destination / "readback.json", (json.dumps(root_readback, indent=2) + "\n").encode())
result = {
    "observed_at": datetime.now(UTC).isoformat(),
    "campaign": number,
    "source_claim_sha256": hashlib.sha256(claim_raw).hexdigest(),
    "original_bootstrap_sha256": bootstrap_sha,
    "snapshot": snapshot,
    "root_files": root_readback["file_count"],
    "root_bytes": root_readback["bytes"],
    "ordinary_autonomous_export_seal_reconstructed": False,
    "new_hosts_models_sandboxes": 0,
    "originals_changed": False,
    "scope": "Original quiescent fallback snapshot and root export readback; no task acceptance.",
}
save_original(
    root / "failure-archive-readback.json", (json.dumps(result, indent=2) + "\n").encode()
)
print(json.dumps(result), flush=True)
