"""Run only inside the disposable sandbox; record bounded plain-script evidence."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib
from pathlib import Path


class InvalidStagedInputs(ValueError):
    """A declared input cannot be admitted; the setup worker may fix its recipe."""


def stage_inputs(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    root = Path("/inputs")
    root.mkdir(exist_ok=True)
    records = []
    for item in manifest["data_source"]["files"]:
        name = item["name"]
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("Input inventory requires plain filenames")
        path = root / name
        sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
        with urllib.request.urlopen(item["url"], timeout=60) as response, path.open("xb") as output:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > item["bytes"]:
                    raise ValueError("Input exceeds recorded size")
                output.write(chunk)
                sha256.update(chunk)
                md5.update(chunk)
        if size != item["bytes"] or md5.hexdigest() != item["provider_md5"]:
            raise ValueError("Input inventory checksum or size mismatch")
        records.append(
            {
                **item,
                "local_path": str(path),
                "sha256": sha256.hexdigest(),
                "provider_checksum_verified": True,
            }
        )
    Path("/work/staged-inputs.json").write_text(json.dumps({"files": records}, indent=2))
    print(json.dumps({"files": records}), flush=True)


def verify_inputs():
    records = json.loads(Path("/work/staged-inputs.json").read_text())["files"]
    for item in records:
        with Path(item["local_path"]).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != item["sha256"]:
            raise ValueError("Original staged input changed")
    print(json.dumps({"original_inputs_unchanged": True, "files": len(records)}), flush=True)


def input_preview(path):
    """Expose original bytes for inspection; never infer a schema or header."""
    with path.open("rb") as stream:
        compressed = stream.read(2) == b"\x1f\x8b"
    try:
        opener = gzip.open if compressed else open
        with opener(path, "rb") as stream:
            raw = stream.read(4097)
    except (OSError, EOFError, zlib.error) as error:
        return {"status": "unavailable", "error_type": type(error).__name__}
    prefix = raw[:4096]
    result = {
        "compression": "gzip" if compressed else "none",
        "sampled_bytes": len(prefix),
        "sample_sha256": hashlib.sha256(prefix).hexdigest(),
        "byte_prefix_truncated": len(raw) > len(prefix),
        "scope": "Byte prefix only; no inferred header, schema or record count.",
    }
    try:
        text = prefix.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is None or any(ord(c) < 32 and c not in "\t\n\r" for c in text):
        result.update(status="raw_hex_prefix", hex=prefix[:64].hex())
    else:
        lines = text.splitlines(keepends=True)
        result.update(
            status="utf8_text_prefix",
            text="".join(lines[:5]),
            displayed_lines_truncated=len(lines) > 5,
        )
    return result


def snapshot_inputs(manifest_path, receipt_path, roots=(Path("/inputs"), Path("/work/cache"))):
    """Hash the worker's declared input/cache files; never trust worker hashes."""
    manifest = json.loads(Path(manifest_path).read_text())
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise InvalidStagedInputs("Input manifest requires a files array")
    records = []
    seen = set()
    for index, item in enumerate(manifest["files"]):
        if not isinstance(item, dict) or any(
            not isinstance(item.get(k), str) or not item[k] for k in ("local_path", "source")
        ):
            raise InvalidStagedInputs(f"Input {index} needs local_path and source")
        path = Path(item["local_path"])
        if (
            not path.is_absolute()
            or str(path) in seen
            or not any(path.resolve().is_relative_to(root.resolve()) for root in roots)
            or not path.is_file()
        ):
            raise InvalidStagedInputs(f"Invalid staged input path for input {index}: {path}")
        seen.add(str(path))
        with path.open("rb") as stream:
            sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        records.append(
            {
                "local_path": str(path),
                "source": item["source"],
                "bytes": path.stat().st_size,
                "sha256": sha256,
                "input_preview": input_preview(path),
            }
        )
    receipt = {"files": records}
    Path(receipt_path).write_text(json.dumps(receipt, indent=2))
    return receipt


def verify_staging(receipt_path, roots=(Path("/inputs"), Path("/work/cache"))):
    """Validate and rehash declared staged files before admitting execution."""
    receipt = json.loads(Path(receipt_path).read_text())
    if not isinstance(receipt, dict) or not isinstance(receipt.get("files"), list):
        raise ValueError("Staging receipt must contain a files array")
    seen = set()
    for item in receipt["files"]:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(key), str) or not item[key]
            for key in ("local_path", "source", "sha256")
        ):
            raise ValueError("Staged files require local_path, source and sha256")
        path = Path(item["local_path"])
        if (
            not path.is_absolute()
            or str(path) in seen
            or not any(path.resolve().is_relative_to(root.resolve()) for root in roots)
            or not re.fullmatch("[0-9a-f]{64}", item["sha256"])
        ):
            raise ValueError("Invalid staged file path or SHA-256")
        seen.add(str(path))
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != item["sha256"]:
            raise ValueError("Staged file checksum mismatch")
    return {"staged_inputs_verified": True, "files": len(seen)}


def execute(argv, timeout, directory, label):
    log = Path("/work/logs") / (label + ".log")
    log.parent.mkdir(exist_ok=True)
    started = time.time()
    # Keep the live output on an anonymous file descriptor. A setup worker may
    # legitimately clean its workspace, including old logs; unlinking a named
    # active log must not destroy the controller's only copy of command output.
    with tempfile.TemporaryFile(mode="w+b") as stream:
        process = subprocess.Popen(
            argv, cwd=directory, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
        )
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
        finally:
            # Do not leave a background child from setup or analysis alive.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stream.seek(0)
        log.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=log.parent, delete=False) as saved:
            saved_path = Path(saved.name)
            try:
                shutil.copyfileobj(stream, saved, length=1024 * 1024)
            except BaseException:
                saved_path.unlink(missing_ok=True)
                raise
        try:
            os.replace(saved_path, log)
        finally:
            saved_path.unlink(missing_ok=True)
    record = {
        "argv": argv,
        "directory": directory,
        "label": label,
        "timeout_seconds": timeout,
        "started": started,
        "finished": time.time(),
        "exit_code": code,
        "timed_out": timed_out,
        "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "rss_limitations": "Maximum child RSS, not aggregate sandbox or simultaneous-process memory",
    }
    record["elapsed_seconds"] = record["finished"] - started
    with log.open("rb") as stream:
        record["log_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    # A reconnecting reader must see either no receipt or a complete receipt.
    with tempfile.NamedTemporaryFile(dir=log.parent, mode="w", delete=False) as receipt:
        receipt_path = Path(receipt.name)
        try:
            json.dump(record, receipt, indent=2)
        except BaseException:
            receipt_path.unlink(missing_ok=True)
            raise
    try:
        os.replace(receipt_path, Path("/work/logs", label + ".json"))
    finally:
        receipt_path.unlink(missing_ok=True)
    print(json.dumps(record), flush=True)


def inventory(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    results = []
    for artifact in plan["artifacts"]:
        path = Path("/work/outputs") / artifact["path"]
        item = {"path": artifact["path"], "exists": path.is_file()}
        if path.is_symlink() or not path.resolve().is_relative_to(Path("/work/outputs")):
            raise ValueError("Artifacts must be regular files within the output directory")
        if item["exists"]:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            item.update(bytes=path.stat().st_size, sha256=digest.hexdigest())
        results.append(item)
    print(
        json.dumps(
            {
                "artifacts": results,
                "declared_artifacts_present": all(
                    row["exists"] and row["bytes"] > 0 for row in results
                ),
                "semantic_fidelity_validated": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    if sys.argv[1] == "stage-inputs":
        stage_inputs(sys.argv[2])
    elif sys.argv[1] == "verify-inputs":
        verify_inputs()
    elif sys.argv[1] == "snapshot-inputs":
        try:
            result = snapshot_inputs(sys.argv[2], sys.argv[3])
        except InvalidStagedInputs as error:
            result = {"input_validation_error": str(error)}
        print(json.dumps(result), flush=True)
    elif sys.argv[1] == "verify-staging":
        print(json.dumps(verify_staging(sys.argv[2])), flush=True)
    elif sys.argv[1] == "inventory":
        inventory(sys.argv[2])
    else:
        execute(json.loads(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
