"""Read only original export seals; never infer a missing archive is complete."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rigging.filesystem.buckets import filesystem_for

number = int(sys.argv[1])
assert number in range(196, 206)
prefix = (
    "s3://marin-us-east-02a/marin/evals/biotasks19/20261026-panel101/"
    f"biotasks19-autonomous-panel-{number:03}/"
)
root = Path(f"/home/exedev/.local/share/biotasks/handoffs/issue-19/archives/{number:03}")
observations = root / "bootstrap-evidence"
observations.mkdir(parents=True, exist_ok=True, mode=0o700)
rows = []
for relative in (
    "export-manifest.json",
    "autonomous/export-manifest.json",
    "autonomous-snapshot/export-manifest.json",
):
    fs, key = filesystem_for(prefix + relative)
    try:
        with fs.open(key, "rb", cache_type="none", block_size=1024 * 1024) as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
    except FileNotFoundError:
        rows.append({"path": relative, "present": False})
        continue
    assert len(raw) <= 8 * 1024 * 1024
    data = json.loads(raw)
    sha = hashlib.sha256(raw).hexdigest()
    destination = observations / (sha + "-original-export-manifest.json")
    if destination.exists():
        assert destination.read_bytes() == raw
    else:
        destination.write_bytes(raw)
        destination.chmod(0o600)
    rows.append(
        {
            "path": relative,
            "present": True,
            "sha256": sha,
            "bytes": len(raw),
            "download_checked": data.get("download_checked"),
            "file_count": len(data.get("files", [])),
            "object_bytes": sum(row["bytes"] for row in data.get("files", [])),
        }
    )
result = {
    "observed_at": datetime.now(UTC).isoformat(),
    "campaign": number,
    "original_export_seals": rows,
    "new_jobs_models_sandboxes": 0,
    "scope": "Seal presence only; no scientific acceptance or complete archive readback.",
}
raw = (json.dumps(result, indent=2) + "\n").encode()
destination = observations / (hashlib.sha256(raw).hexdigest() + "-export-presence.json")
destination.write_bytes(raw)
assert destination.read_bytes() == raw
print(json.dumps(result), flush=True)
