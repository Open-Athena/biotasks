"""Freeze follow-up inputs and bind them to a settled worker's artifact receipt.

Only small execution records enter this envelope. The remote bootstrap restores
biological inputs and generated artifacts from their recorded hashes. Preparing
an envelope does not select a scientific disposition or authorize a model call.
"""

import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

from biotasks.factory_dispatch import STAGE_SLOTS, session_identity
from biotasks.factory_stage import stage_spec

MAX_ENVELOPE_BYTES = 32 * 1024 * 1024


def encode(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def record_path(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or str(path) != name
        or name == "handoff.json"
    ):
        raise ValueError("Unsafe or reserved parent record path")
    return "parent-records/" + name


def freeze_followup(
    root_batch: Path,
    root_sha256: str,
    seed: str,
    slot: str,
    parent_session: dict,
    restore_descriptor: dict,
    records: dict[str, bytes],
    request_cap: int,
    wall_seconds: int,
    archive: Path,
    output: Path,
) -> dict:
    """Create immutable stage inputs; keep the original batch and limits intact.

    The dispatcher independently checks the predecessor against its durable
    ledger. The worker independently checks this envelope, the descriptor, every
    restored artifact, all supplied records, and the final candidate manifest.
    """
    raw = root_batch.read_bytes()
    if hashlib.sha256(raw).hexdigest() != root_sha256:
        raise ValueError("Original batch hash mismatch")
    batch = json.loads(raw)
    if "root_batch_sha256" in batch:
        raise ValueError("Use the original batch, not another follow-up")
    if slot not in STAGE_SLOTS or slot == "authoring":
        raise ValueError("A follow-up workflow slot is required")
    role, previous = STAGE_SLOTS[slot]
    assert previous is not None
    expected = session_identity(root_sha256, seed, previous)
    if parent_session.get("session_id") != expected:
        raise ValueError("Wrong predecessor for follow-up slot")
    initial = batch["entries"][seed]
    for proposed, ceiling in (
        (request_cap, initial["request_cap"]),
        (wall_seconds, initial["wall_seconds"]),
    ):
        if type(proposed) is not int or not 1 <= proposed <= ceiling:
            raise ValueError("Follow-up expands the frozen session limits")
    if archive.exists() or output.exists():
        raise FileExistsError("Follow-up files already exist")
    if not records or any(not isinstance(value, bytes) for value in records.values()):
        raise ValueError("Preserved parent execution records required")
    descriptor = dict(restore_descriptor)
    descriptor["record_files"] = [
        {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(records.items())
    ]
    descriptor_bytes = encode(descriptor)
    members = {record_path(name): data for name, data in records.items()}
    members["parent-restore.json"] = descriptor_bytes
    if sum(map(len, members.values())) > MAX_ENVELOPE_BYTES:
        raise ValueError("Parent evidence exceeds bounded envelope size")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as target:
        for name, content in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            target.writestr(info, content)
    spec = stage_spec(role, archive, request_cap, wall_seconds)
    spec["output_cap"] = initial["output_cap"]
    spec["stage_slot"] = slot
    spec["predecessor"] = {
        **parent_session,
        "artifact_receipt_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
    }
    followup = {
        "schema_version": 1,
        "status": "prepared_not_submitted",
        "factory_revision": batch["factory_revision"],
        "root_batch_sha256": root_sha256,
        "execution_budget_sha256": batch.get("execution_budget_sha256"),
        "protocol": batch["protocol"],
        "entries": {seed: spec},
        "automatic_retries": 0,
    }
    encoded = encode(followup)
    with output.open("xb") as destination:
        destination.write(encoded)
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "input_zip_sha256": spec["input_zip_sha256"],
        "session_id": session_identity(root_sha256, seed, slot),
    }
