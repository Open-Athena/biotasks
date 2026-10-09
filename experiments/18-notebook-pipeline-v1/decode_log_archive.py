"""Verify and decode an early or final text export from preserved job log lines."""

import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path


def decode(log_path, destination, stage="final"):
    if stage not in {"early", "final"}:
        raise ValueError("Unknown export stage")
    if destination.exists():
        raise ValueError("Decode destination already exists")
    if log_path.stat().st_size > 8 * 1024**2:
        raise ValueError("Log exceeds bounded local decoder size; recover on remote compute")
    rows = json.loads(log_path.read_text())
    if not isinstance(rows, list) or not all(isinstance(row, str) for row in rows):
        raise ValueError("Expected a JSON list of preserved log strings")
    prefix = "BIOTASKS_AUTHOR_EARLY" if stage == "early" else "BIOTASKS_SMOKE"
    metadata = []
    chunks = {}
    for row in rows:
        if prefix + "_ARCHIVE " in row:
            metadata.append(json.loads(row.split(prefix + "_ARCHIVE ", 1)[1]))
        if prefix + "_CHUNK " in row:
            index, value = row.split(prefix + "_CHUNK ", 1)[1].split(" ", 1)
            index = int(index)
            if index in chunks:
                raise ValueError("Duplicate chunk index")
            chunks[index] = value.strip()
    if len(metadata) != 1:
        raise ValueError("Expected exactly one archive header for the selected stage")
    meta = metadata[0]
    if not isinstance(meta["chunks"], int) or not 1 <= meta["chunks"] <= 2000:
        raise ValueError("Invalid chunk count")
    if set(chunks) != set(range(meta["chunks"])):
        raise ValueError("Missing or unexpected chunks")
    packed = base64.b64decode("".join(chunks[i] for i in range(meta["chunks"])), validate=True)
    if hashlib.sha256(packed).hexdigest() != meta["sha256"]:
        raise ValueError("Compressed export checksum mismatch")
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as archive:
        unpacked = archive.read(32 * 1024**2 + 1)
    if len(unpacked) > 32 * 1024**2:
        raise ValueError("Decompressed text exceeds bounded local decoder size")
    artifacts = json.loads(unpacked)
    if not isinstance(artifacts, dict):
        raise ValueError("Expected an artifact dictionary")
    for name, value in artifacts.items():
        path = Path(name)
        if not isinstance(value, str) or path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe artifact path or non-text value")
        if not (destination / path).resolve().is_relative_to(destination.resolve()):
            raise ValueError("Artifact escapes decode directory")
    destination.mkdir(parents=True)
    for name, value in artifacts.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x") as stream:
            stream.write(value)
    return {
        "stage": stage,
        "export_sha256": meta["sha256"],
        "files": len(artifacts),
        "complete_binary_artifact_recovery": False,
        "scope": "Early checkpoint is partial; final text export still excludes large/binary assets",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--stage", choices=["early", "final"], default="final")
    args = parser.parse_args()
    print(json.dumps(decode(args.logs, args.destination, args.stage), indent=2))
