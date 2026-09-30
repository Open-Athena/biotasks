"""Inventory retained local evidence without copying provider responses into Git."""

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
excluded = {
    "uv-cache",
    "biotasks-docs-site",
    "integration-docs-baseline",
    "integration-docs-baseline.tar",
    "__pycache__",
}
files = []


def visit(directory):
    for path in sorted(directory.iterdir()):
        if path.name in excluded or path.is_symlink():
            continue
        if path.is_dir():
            visit(path)
        elif path.is_file():
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            files.append(
                {
                    "path": str(path.relative_to(root)),
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                    "disposition": "retained-at-source",
                }
            )


visit(root)
print(
    json.dumps(
        {
            "source_root": str(root),
            "durable_archive": False,
            "retention": "Keep in place pending a durable storage decision; no deletion authorized. File hashes do not constitute an archive.",
            "exclusions": sorted(excluded),
            "files": files,
            "total_bytes": sum(p["bytes"] for p in files),
        },
        indent=2,
    )
)
