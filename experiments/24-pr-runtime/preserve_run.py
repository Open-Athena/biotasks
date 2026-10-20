"""Copy reviewed run diagnostics and a sanitized receipt from private readback."""

import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path


def timestamp(value):
    return datetime.datetime.fromisoformat(value.removeprefix("Timestamp(").removesuffix(")"))


def preserve(source, observation, destination, source_commit, disposition, archive_path):
    attempt = observation["attempts"][-1]
    archive = attempt["output_archive"]
    assert archive_path.stat().st_size == archive["size_bytes"]
    digest = hashlib.sha256()
    with archive_path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    assert digest.hexdigest() == archive["sha256"]
    duration = (timestamp(attempt["finished_at"]) - timestamp(attempt["started_at"])).total_seconds()
    report = source / "development-result.json"
    report_hash = hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None
    if report_hash:
        emitted = [line.split("BIOTASKS24_DEVELOPMENT_SHA256 ", 1)[1].strip()
                   for line in observation["logs"] if "BIOTASKS24_DEVELOPMENT_SHA256 " in line]
        assert emitted == [report_hash]
    destination.mkdir(parents=True, exist_ok=True)
    names = {"development-result.json", "runner-packages.txt", "target-packages.txt",
             "runner-filesystem.json", "docker-client-version.txt", "runner-failure.json"}
    for path in source.iterdir():
        if path.name in names or path.name.startswith(("build-", "control-", "export-")):
            shutil.copyfile(path, destination / path.name)
    receipt = {
        "state": observation["state"], "attempt_exit_code": attempt["exit_code"],
        "source_commit": source_commit, "started_at": attempt["started_at"],
        "finished_at": attempt["finished_at"], "elapsed_attempt_seconds": duration,
        "allocated_cpu_hours": 3 * duration / 3600, "actual_cpu_usage": "unavailable",
        "resources": {"cpu": 3, "memory": "10GB", "disk": "30GB"},
        "model_calls": 0, "archive_sha256": archive["sha256"],
        "archive_bytes": archive["size_bytes"], "readback_verified": True,
        "report_sha256": report_hash, "disposition": disposition,
        "accepted_tasks": 0,
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (destination / "archive-file-hashes.json").write_text(json.dumps({
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(source.iterdir()) if p.is_file() and p.name != "outputs.tar.zst"
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("observation", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--disposition", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    preserve(args.source, json.loads(args.observation.read_text()), args.destination,
             args.source_commit, args.disposition, args.archive)
