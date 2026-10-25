"""Content-addressed local evidence and append-only, anonymously verified HF copies."""

import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from biotasks.validation.archives import records
from biotasks.validation.files import (
    ValidationError,
    inventory,
    read_json,
    require,
    safe,
    sha,
    write_json,
)

TRANSFER_LIMITS = {
    "HF_HUB_DISABLE_PROGRESS_BARS": "1",
    "HF_XET_HIGH_PERFORMANCE": "0",
    "HF_XET_CLIENT_ENABLE_ADAPTIVE_CONCURRENCY": "false",
    "HF_XET_CLIENT_AC_INITIAL_UPLOAD_CONCURRENCY": "1",
    "HF_XET_CLIENT_AC_MIN_UPLOAD_CONCURRENCY": "1",
    "HF_XET_CLIENT_AC_MAX_UPLOAD_CONCURRENCY": "1",
    "HF_XET_CLIENT_AC_INITIAL_DOWNLOAD_CONCURRENCY": "1",
    "HF_XET_CLIENT_AC_MIN_DOWNLOAD_CONCURRENCY": "1",
    "HF_XET_CLIENT_AC_MAX_DOWNLOAD_CONCURRENCY": "1",
    "HF_XET_DATA_MAX_CONCURRENT_FILE_INGESTION": "1",
    "HF_XET_DATA_MAX_CONCURRENT_FILE_DOWNLOADS": "1",
    "HF_XET_DATA_INGESTION_BLOCK_SIZE": "1mb",
    "HF_XET_RECONSTRUCTION_MIN_RECONSTRUCTION_FETCH_SIZE": "1mb",
    "HF_XET_RECONSTRUCTION_MAX_RECONSTRUCTION_FETCH_SIZE": "16mb",
    "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_SIZE": "32mb",
    "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_PERFILE_SIZE": "16mb",
    "HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_LIMIT": "64mb",
    "HF_XET_RECONSTRUCTION_MIN_PREFETCH_BUFFER": "1mb",
    "HF_XET_SHARD_CHUNK_INDEX_TABLE_MAX_SIZE": "8388608",
    "HF_XET_SHARD_CACHE_SIZE_LIMIT": "16mb",
    "HF_XET_CHUNK_CACHE_SIZE_BYTES": "0",
    "TOKIO_WORKER_THREADS": "1",
}


@contextmanager
def transfer_limits(directory: Path) -> Iterator[None]:
    cache = directory / "hf-transfer-cache"
    require(not cache.is_symlink(), "Symlinked transfer cache")
    settings = {**TRANSFER_LIMITS, "HF_XET_CACHE": str(cache)}
    previous = {name: os.environ.get(name) for name in settings}
    os.environ.update(settings)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        if cache.exists():
            shutil.rmtree(cache)


def prepare(directory: Path, sources: dict[str, Path], metadata: dict[str, Any]) -> dict[str, Any]:
    """An atomic local snapshot is required even when publication is withheld."""
    target = directory / "preserved"
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix=".preserve-", dir=directory) as temporary:
            staged = Path(temporary) / "snapshot"
            staged.mkdir()
            data = staged / "files"
            data.mkdir()
            for name, source in sources.items():
                dest = data / safe(name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                require(source.is_file() and not source.is_symlink(), "Missing archive source")
                shutil.copyfile(source, dest)
                with dest.open("rb") as stream:
                    os.fsync(stream.fileno())
            manifest = {
                "schema_version": 1,
                "created_utc": datetime.now(UTC).isoformat(),
                "retention": "Retain while cited; no automatic deletion",
                "metadata": metadata,
                "files": inventory(data),
            }
            write_json(staged / "manifest.json", manifest)
            for folder in [
                *sorted((p for p in staged.rglob("*") if p.is_dir()), reverse=True),
                staged,
            ]:
                descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            staged.rename(target)
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    value = verify(directory)
    require(value["metadata"] == metadata, "Preservation metadata changed")
    require(
        {r["path"]: r["sha256"] for r in value["files"]} == {n: sha(p) for n, p in sources.items()},
        "Preserved source changed",
    )
    return value


def verify(directory: Path) -> dict[str, Any]:
    root = directory / "preserved"
    value = read_json(root / "manifest.json")
    require(inventory(root / "files") == value["files"], "Local preserved evidence changed")
    return value


def inspect(raw: bytes, name: str, depth: int = 0) -> None:
    """Review is explicit in the manifest; scan the exact bounded upload bytes."""
    require(depth <= 4, "Nested archive depth bound")
    if name.endswith((".tar.gz", ".tar.zst")):
        for member, row in records(raw, "tar.gz" if name.endswith(".gz") else "tar.zst").items():
            inspect(row["data"], member, depth + 1)
        return
    try:
        raw.decode("utf-8")
    except UnicodeError as error:
        raise ValidationError("Non-text public archive member: " + name) from error
    require(
        b"\x00" not in raw and b"GIT binary patch" not in raw and b"data:image/" not in raw,
        "Binary/embedded-data public archive member",
    )
    require(
        not re.search(
            rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-or-v1-[0-9a-f]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|https?://[^/\s:@]+:[^/\s@]+@)",
            raw,
        ),
        "Credential-shaped bytes in public archive",
    )
    require(
        Path(name).name not in (".env", "credentials.env", "hosts.yml"),
        "Credential file in public archive",
    )


def _publish(directory: Path, archive: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    manifest = verify(directory)
    manifest_path = directory / "preserved/manifest.json"
    digest = sha(manifest_path)
    if archive["kind"] == "local" or not policy["eligible"]:
        receipt = {
            "kind": "local",
            "manifest_sha256": digest,
            "local_readback_verified": True,
            "public_state": "not_requested"
            if archive["kind"] == "local"
            else "withheld_ineligible",
            "retention": manifest["retention"],
        }
    else:
        require(bool(policy.get("review")), "No publication review record")
        from huggingface_hub import HfApi

        api = HfApi()
        bucket = archive["bucket"]
        require(not api.bucket_info(bucket).private, "Expected a public HF bucket")
        prefix = archive["prefix"].strip("/") + "/" + manifest["created_utc"][:10] + "/" + digest
        objects = {
            "manifest.json": manifest_path,
            **{r["path"]: directory / "preserved/files" / r["path"] for r in manifest["files"]},
        }
        for name, file in objects.items():
            inspect(file.read_bytes(), name)
        expected = {prefix + "/" + name for name in objects}
        existing = {
            f.path
            for f in api.list_bucket_tree(bucket, prefix=prefix, recursive=True)
            if f.type == "file"
        }
        intent = directory / "publication-intent.json"
        binding = {"bucket": bucket, "prefix": prefix, "manifest_sha256": digest}
        if intent.exists():
            require(read_json(intent) == binding, "Publication intent changed")
        else:
            require(not existing, "Refuse an existing snapshot without this run's intent")
            write_json(intent, binding)
        require(existing <= expected, "Unexpected existing object; never overwrite or delete")
        verified = []
        with tempfile.TemporaryDirectory(prefix=".anonymous-readback-", dir=directory) as temporary:
            # Refuse changed existing bytes before making any new writes.
            for name, source in objects.items():
                remote = prefix + "/" + name
                if remote in existing:
                    dest = Path(temporary) / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    api.download_bucket_files(
                        bucket, [(remote, dest)], token=False, raise_on_missing_files=True
                    )
                    require(
                        dest.stat().st_size == source.stat().st_size and sha(dest) == sha(source),
                        "Anonymous readback differs; never overwrite",
                    )
            missing: list[tuple[str | Path | bytes, str]] = [
                (str(source), prefix + "/" + name)
                for name, source in objects.items()
                if prefix + "/" + name not in existing
            ]
            if missing:
                # Transfer concurrency remains one; batch the API handoff rather
                # than paying a separate upload session for every small object.
                api.batch_bucket_files(bucket, add=missing)
            for name, source in objects.items():
                remote = prefix + "/" + name
                dest = Path(temporary) / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if remote not in existing:
                    api.download_bucket_files(
                        bucket, [(remote, dest)], token=False, raise_on_missing_files=True
                    )
                require(
                    dest.stat().st_size == source.stat().st_size and sha(dest) == sha(source),
                    "Anonymous readback differs; never overwrite",
                )
                verified.append({"path": remote, "bytes": dest.stat().st_size, "sha256": sha(dest)})
        receipt = {
            **binding,
            "kind": "hf-public",
            "anonymous_download_verified": True,
            "objects": verified,
            "overwrites": False,
            "retention": manifest["retention"],
            "transfer_limits": TRANSFER_LIMITS,
        }
    path = directory / "publication.json"
    if path.exists():
        require(read_json(path) == receipt, "Publication receipt changed")
    else:
        write_json(path, receipt)
    return receipt


def publish(directory: Path, archive: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    with transfer_limits(directory):
        return _publish(directory, archive, policy)


def verify_receipt(directory: Path) -> None:
    manifest = verify(directory)
    receipt = read_json(directory / "publication.json")
    require(
        receipt["manifest_sha256"] == sha(directory / "preserved/manifest.json"),
        "Publication manifest changed",
    )
    if receipt["kind"] == "local":
        require(receipt["local_readback_verified"] is True, "Local readback missing")
    else:
        require(
            receipt["kind"] == "hf-public" and receipt["anonymous_download_verified"] is True,
            "Public readback missing",
        )
        expected = {
            "manifest.json": receipt["manifest_sha256"],
            **{r["path"]: r["sha256"] for r in manifest["files"]},
        }
        require(
            {
                r["path"].removeprefix(receipt["prefix"] + "/"): r["sha256"]
                for r in receipt["objects"]
            }
            == expected,
            "Incomplete publication receipt",
        )
