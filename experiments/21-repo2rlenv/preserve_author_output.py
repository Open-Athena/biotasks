"""Save bounded author evidence to Iris's supported per-attempt output directory.

This is temporary recovery storage, not a public release or a substitute for
the verified Hugging Face snapshots. No environment or credential files are read.
"""

import hashlib
import json
import tarfile
from pathlib import Path


def preserve(source: Path, output: Path, *, max_bytes: int = 128 * 1024**2):
    source = source.resolve()
    output = output.resolve()
    if output == source or source in output.parents:
        raise ValueError("Recovery output must be outside the author directory")
    files = []
    total = 0
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("Linked author evidence requires separate review")
        if path.is_file():
            total += path.stat().st_size
            if total > max_bytes:
                raise ValueError("Author evidence exceeds the recovery size bound")
            files.append(path)
    if not source.is_dir() or not files:
        raise ValueError("No author evidence to preserve")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "author-evidence.tar.gz"
    if target.exists():
        raise FileExistsError(target)
    pending = output / "author-evidence.tar.gz.partial"
    try:
        with pending.open("xb") as stream:
            with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                for path in files:
                    archive.add(path, arcname=str(Path("author-output") / path.relative_to(source)))
        digest = hashlib.sha256()
        with pending.open("rb") as stream:
            for block in iter(lambda: stream.read(65536), b""):
                digest.update(block)
        receipt = {"stage": "temporary_author_evidence_recovery", "files": len(files),
                   "uncompressed_bytes": total, "archive_bytes": pending.stat().st_size,
                   "sha256": digest.hexdigest(), "public_release": False}
        pending.rename(target)
        (output / "author-evidence-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
    finally:
        pending.unlink(missing_ok=True)
