"""Inspect a hash-pinned wheel without installing or importing its contents.

This records a static archive inventory and exact serialized reference matches.
It does not prove that no semantically equivalent answers exist in package code.
"""

import argparse
import hashlib
import json
import tempfile
import tomllib
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


def inspect(lock, distribution, reference, output, related_tokens):
    packages = tomllib.loads(lock.read_text())["package"]
    selected = [package for package in packages if package["name"] == distribution]
    if len(selected) != 1 or len(selected[0].get("wheels", [])) != 1:
        raise ValueError("Select a locked distribution with exactly one wheel")
    package = selected[0]
    wheel = package["wheels"][0]
    url = urllib.parse.urlparse(wheel["url"])
    if url.scheme != "https" or url.hostname != "files.pythonhosted.org":
        raise ValueError("Only the recorded public PyPI artifact host is supported")
    references = {}
    for path in reference.rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            references[path.relative_to(reference).as_posix()] = {
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
    rows, matches = [], []
    with tempfile.TemporaryDirectory(prefix="biotasks19-wheel-audit-") as temporary:
        archive = Path(temporary) / "wheel.zip"
        digest, size = hashlib.sha256(), 0
        with (
            urllib.request.urlopen(wheel["url"], timeout=30) as response,
            archive.open("wb") as target,
        ):
            while chunk := response.read(65536):
                size += len(chunk)
                if size > wheel["size"]:
                    raise ValueError("Artifact exceeds its locked byte count")
                digest.update(chunk)
                target.write(chunk)
        if size != wheel["size"] or "sha256:" + digest.hexdigest() != wheel["hash"]:
            raise ValueError("Artifact differs from the lock")
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if member.is_dir():
                    continue
                with zipped.open(member) as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                rows.append({"path": member.filename, "bytes": member.file_size, "sha256": digest})
                for name, recorded in references.items():
                    if recorded == {"bytes": member.file_size, "sha256": digest}:
                        matches.append({"archive_path": member.filename, "reference_path": name})
    result = {
        "distribution": distribution,
        "version": package["version"],
        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "wheel": wheel,
        "wheel_hash_and_size_checked": True,
        "files": rows,
        "related_path_tokens": related_tokens,
        "related_files": [
            row for row in rows if any(token in row["path"] for token in related_tokens)
        ],
        "references": references,
        "exact_serialized_reference_matches": matches,
        "scope": "Static hash-pinned wheel inventory and exact serialized-byte comparison, not a runtime installation inventory or proof of semantic answer absence. No package code was imported or executed.",
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--related-path-token", action="append", default=[])
    args = parser.parse_args()
    result = inspect(
        args.lock, args.distribution, args.reference_dir, args.output, args.related_path_token
    )
    print(
        json.dumps(
            {
                "files": len(result["files"]),
                "exact_serialized_reference_matches": result["exact_serialized_reference_matches"],
                "package_code_executed": False,
            }
        )
    )
