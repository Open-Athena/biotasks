"""Assemble a candidate from preserved author input plus generated-file overlay.

This is an explicit assembly, not a claim to recover unrecorded deletions from
the author workspace. Review the assembled package and pin its manifest before
native validation. Stream all biological files; never execute source on intake.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def safe_path(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes assembly directory")
    return path


def copy_checked(open_remote, uri, path, expected_sha256, expected_size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with open_remote(uri, "rb") as source, path.open("wb") as target:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > 1024**3 or expected_size is not None and size > expected_size:
                raise ValueError("Artifact exceeds recorded size or 1 GiB per-file limit")
            digest.update(chunk)
            target.write(chunk)
    if digest.hexdigest() != expected_sha256 or expected_size is not None and size != expected_size:
        raise ValueError("Artifact checksum/size mismatch")


def restore(
    open_remote,
    prefix,
    destination,
    input_sha256,
    generated_manifest,
    parent_workspace=None,
    require_task=True,
):
    """Use a caller-supplied authenticated opener; credentials never enter records."""
    if destination.exists():
        raise ValueError("Assembly destination already exists")
    if sum(entry["size"] for entry in generated_manifest) > 4 * 1024**3:
        raise ValueError("Generated artifacts exceed this worker's 4 GiB assembly budget")
    destination.mkdir(parents=True)
    archive_path = destination / "author-input.zip"
    copy_checked(open_remote, prefix + "/inputs.zip", archive_path, input_sha256)
    workspace = destination / "workspace"
    if parent_workspace is not None:
        shutil.copytree(parent_workspace, workspace)
    else:
        workspace.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        total = 0
        for member in archive.infolist():
            path = safe_path(workspace, member.filename)
            total += member.file_size
            if member.file_size > 1024**3 or total > 4 * 1024**3:
                raise ValueError("Input archive exceeds assembly budget")
            if member.is_dir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            # Do not recreate links or execute archive members.
            with archive.open(member) as source, path.open("wb") as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
    for entry in generated_manifest:
        relative = entry["path"]
        copy_checked(
            open_remote,
            prefix + "/workspace/" + relative,
            safe_path(workspace, relative),
            entry["sha256"],
            entry["size"],
        )
    task = workspace / "task"
    if require_task and not task.is_dir():
        raise ValueError("No candidate task directory in preserved assembly")
    manifest = []
    for path in sorted(task.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        manifest.append(
            {
                "path": str(path.relative_to(task)),
                "size": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    (destination / "assembly-manifest.json").write_text(
        json.dumps(
            {
                "method": "preserved-input-plus-generated-overlay",
                "input_sha256": input_sha256,
                "parent_workspace_used": parent_workspace is not None,
                "unrecorded_deletions_reconstructed": False,
                "task_files": manifest,
            },
            indent=2,
        )
        + "\n"
    )
    return workspace
