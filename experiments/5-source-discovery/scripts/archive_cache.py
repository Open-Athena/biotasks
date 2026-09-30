"""One-off migration archive: prepare locally, then upload and verify a public snapshot.

Run under run_bounded.py. Transfer requires huggingface_hub==1.6.0 and hf-xet==1.6.0.
This is an experiment helper, not a supported BioTasks storage CLI.
"""

import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_archive(path, manifest):
    expected = {item["path"]: item for item in manifest["files"]}
    seen = set()
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if not member.isfile() or member.name not in expected or member.name in seen:
                raise ValueError(f"Unexpected archive member: {member.name}")
            item = expected[member.name]
            with archive.extractfile(member) as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if member.size != item["bytes"] or actual != item["sha256"]:
                raise ValueError(f"Archive mismatch: {member.name}")
            seen.add(member.name)
    if seen != set(expected):
        raise ValueError("Archive member set is incomplete")
    return len(seen)


def prepare(args):
    inventory = json.loads(args.inventory.read_text())
    root = Path(inventory["source_root"]).resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    files = [{key: item[key] for key in ("path", "bytes", "sha256")} for item in inventory["files"]]
    if len({item["path"] for item in files}) != len(files):
        raise ValueError("Duplicate inventory paths")
    # High-confidence token patterns only; this is not a redistribution review.
    secret = re.compile(
        rb"(?:hf_[A-Za-z0-9]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:or-v1-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
    )
    for item in files:
        relative = PurePosixPath(item["path"])
        path = root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or path.is_symlink()
            or not path.resolve().is_relative_to(root)
        ):
            raise ValueError("Unsafe inventory path")
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"Source changed since inventory: {relative}")
        with path.open("rb") as handle:
            overlap = b""
            while chunk := handle.read(1024 * 1024):
                if secret.search(overlap + chunk):
                    raise ValueError(f"Possible credential in {relative}; value suppressed")
                overlap = chunk[-4096:]
    manifest = {
        "schema_version": 1,
        "issue": "https://github.com/Open-Athena/biotasks/issues/5",
        "migration_issue": "https://github.com/Open-Athena/biotasks/issues/2",
        "source_inventory": str(args.inventory),
        "source_inventory_sha256": digest(args.inventory),
        "research_checkpoint": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_root": str(root),
        "scope": "Exact allowlisted cache bytes, including partial and failed provider responses; not a scientific validation or public data release.",
        "exclusions": inventory["exclusions"],
        "visibility": "public",
        "retention": "Preserve while cited by research or release evidence. No automatic deletion or overwriting; record any deliberate retention change. Local source is retained.",
        "files": files,
        "total_bytes": sum(item["bytes"] for item in files),
    }
    write_json(args.output / "manifest.json", manifest)
    archive_path = args.output / "cache.tar.gz"
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for item in files:
                    member = tarfile.TarInfo(item["path"])
                    member.size = item["bytes"]
                    member.mode = 0o644
                    member.mtime = 0
                    with (root / item["path"]).open("rb") as source:
                        archive.addfile(member, source)
    count = verify_archive(archive_path, manifest)
    manifest_hash = digest(args.output / "manifest.json")
    plan = {
        "bucket": "open-athena/biotasks",
        "private": False,
        "prefix": f"research/5-source-discovery/2026-09-29/{manifest_hash}",
        "manifest_sha256": manifest_hash,
        "objects": [
            {
                "path": name,
                "bytes": (args.output / name).stat().st_size,
                "sha256": digest(args.output / name),
            }
            for name in ("cache.tar.gz", "manifest.json")
        ],
        "verified_files_before_upload": count,
        "credential_pattern_scan": "No high-confidence token or private-key patterns found; not a complete secret or redistribution audit.",
    }
    write_json(args.output / "plan.json", plan)
    print(json.dumps(plan), flush=True)


def transfer(args):
    # Set before importing the SDK; avoid inherited debug logging and large buffers.
    settings = {
        "HF_DEBUG": "0",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "HF_XET_HIGH_PERFORMANCE": "0",
        "HF_XET_HP": "0",
        "HF_XET_FIXED_UPLOAD_CONCURRENCY": "1",
        "HF_XET_FIXED_DOWNLOAD_CONCURRENCY": "1",
        "HF_XET_DATA_MAX_CONCURRENT_FILE_INGESTION": "1",
        "HF_XET_DATA_MAX_CONCURRENT_FILE_DOWNLOADS": "1",
        "HF_XET_RECONSTRUCTION_MIN_RECONSTRUCTION_FETCH_SIZE": "8mb",
        "HF_XET_RECONSTRUCTION_MAX_RECONSTRUCTION_FETCH_SIZE": "32mb",
        "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_SIZE": "32mb",
        "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_PERFILE_SIZE": "32mb",
        "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_LIMIT": "64mb",
        "HF_XET_RECONSTRUCTION_MIN_PREFETCH_BUFFER": "8mb",
        "HF_XET_SHARD_CHUNK_INDEX_TABLE_MAX_SIZE": "16mb",
        "HF_XET_CACHE": str(args.snapshot / "xet-cache"),
    }
    os.environ.update(settings)
    from huggingface_hub import HfApi
    from huggingface_hub.errors import BucketNotFoundError

    plan = json.loads((args.snapshot / "plan.json").read_text())
    if plan["private"] or plan["bucket"] != "open-athena/biotasks":
        raise ValueError("This migration helper only supports the approved public bucket")
    for item in plan["objects"]:
        path = args.snapshot / item["path"]
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Local snapshot changed since preparation")
    token = (
        os.environ.get("HF_TOKEN") or (Path.home() / ".cache/huggingface/token").read_text().strip()
    )
    api = HfApi(token=token)
    try:
        info = api.bucket_info(plan["bucket"])
    except BucketNotFoundError:
        if args.verify_only:
            raise
        api.create_bucket(plan["bucket"], private=False)
        info = api.bucket_info(plan["bucket"])
    if info.private:
        raise ValueError("Bucket visibility differs from public plan")
    if not args.verify_only:
        existing = list(api.list_bucket_tree(plan["bucket"], prefix=plan["prefix"], recursive=True))
        if existing:
            raise ValueError(
                "Snapshot prefix already exists; refusing to overwrite. Verify or investigate partial state."
            )
        for item in plan["objects"]:
            api.batch_bucket_files(
                plan["bucket"],
                add=[(args.snapshot / item["path"], f"{plan['prefix']}/{item['path']}")],
            )
            print(f"Uploaded {item['path']}", flush=True)
    args.download.mkdir(parents=True, exist_ok=False)
    # Verify the intended public access, not just the uploader's credentials.
    api = HfApi(token=False)
    info = api.bucket_info(plan["bucket"])
    if info.private:
        raise ValueError("Bucket is not public at verification time")
    for item in plan["objects"]:
        target = args.download / item["path"]
        api.download_bucket_files(
            plan["bucket"],
            [(f"{plan['prefix']}/{item['path']}", target)],
            raise_on_missing_files=True,
        )
        if target.stat().st_size != item["bytes"] or digest(target) != item["sha256"]:
            raise ValueError(f"Downloaded object mismatch: {item['path']}")
    manifest = json.loads((args.download / "manifest.json").read_text())
    count = verify_archive(args.download / "cache.tar.gz", manifest)
    receipt = {
        "verified_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "bucket": plan["bucket"],
        "private": info.private,
        "uri": f"hf://buckets/{plan['bucket']}/{plan['prefix']}/",
        "manifest_sha256": plan["manifest_sha256"],
        "verified_objects": plan["objects"],
        "verified_files_after_download": count,
        "download_authentication": "anonymous",
        "total_uncompressed_bytes": manifest["total_bytes"],
        "download_destination": str(args.download),
        "transfer_environment": settings,
        "limits": "Verified bytes and membership by downloading both objects and streaming all archive members. Bucket objects remain mutable; retention is operational, not enforced object locking. Redistribution rights remain unreviewed.",
    }
    write_json(args.receipt, receipt)
    print(json.dumps(receipt), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("inventory", type=Path)
    prepare_parser.add_argument("output", type=Path)
    transfer_parser = commands.add_parser("transfer")
    transfer_parser.add_argument("snapshot", type=Path)
    transfer_parser.add_argument("download", type=Path)
    transfer_parser.add_argument("receipt", type=Path)
    transfer_parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    else:
        transfer(args)


if __name__ == "__main__":
    main()
