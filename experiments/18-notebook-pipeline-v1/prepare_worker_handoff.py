"""Restore a parent candidate byte-for-byte before another GLM worker stage.

Runs remotely with the existing artifact-storage access. No scientific files are
authored here. Missing or inconsistent archives fail before any model call.
"""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

from restore_authoring import restore, safe_path


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def task_manifest(workspace):
    entries = []
    for path in sorted((workspace / "task").rglob("*")):
        if path.is_symlink():
            raise ValueError("Unsupported candidate symlink")
        if path.is_file():
            entries.append(
                {
                    "path": str(path.relative_to(workspace / "task")),
                    "size": path.stat().st_size,
                    "sha256": sha(path),
                }
            )
    return entries


def unpack_handoff(root, spec):
    """Read a bounded, hash-bound envelope without allowing worker code overrides."""
    envelope = root / "handoff.zip"
    if sha(envelope) != spec["input_zip_sha256"]:
        raise ValueError("Submitted handoff differs from the frozen stage")
    with zipfile.ZipFile(envelope) as archive:
        members = archive.infolist()
        names = [entry.filename for entry in members]
        if (
            len(names) != len(set(names))
            or sum(entry.file_size for entry in members) > 32 * 1024**2
        ):
            raise ValueError("Duplicate or oversized handoff envelope")
        if any(entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16) for entry in members):
            raise ValueError("Handoff envelope requires regular files")
        raw = archive.read("parent-restore.json")
        if hashlib.sha256(raw).hexdigest() != spec["predecessor"]["artifact_receipt_sha256"]:
            raise ValueError("Parent restore descriptor differs from the frozen stage")
        parent = json.loads(raw)
        expected = {"parent-restore.json"}
        for record in parent["record_files"]:
            name = record["path"]
            safe_path(root / "parent-records", name)
            if name == "handoff.json" or "parent-records/" + name in expected:
                raise ValueError("Duplicate or reserved parent record path")
            expected.add("parent-records/" + name)
        if set(names) != expected:
            raise ValueError("Unexpected files in handoff envelope")
        for name in names:
            target = safe_path(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    return parent


def prepare(open_remote, root, parent):
    original = root / "inputs.zip"
    prefix = parent["artifact_prefix"]

    def opener(uri, mode):
        if uri == prefix + "/inputs.zip" and original.is_file():
            return original.open(mode)
        return open_remote(uri, mode)

    workspace = restore(
        opener,
        prefix,
        root / "restored",
        parent["input_zip_sha256"],
        parent["generated_manifest"],
        require_task=False,
    )
    for name in parent["deleted_inputs"]:
        target = safe_path(workspace, name)
        if target.is_file():
            target.unlink()
    expected = sorted(parent["task_manifest"], key=lambda entry: entry["path"])
    if task_manifest(workspace) != expected:
        raise ValueError("Restored task differs from final parent manifest")
    evidence = workspace / "previous-run"
    if evidence.exists():
        # Review -> repair -> review preserves earlier stage records rather than
        # overwriting them or failing because the first handoff already exists.
        prior = evidence / "handoff.json"
        if not prior.is_file():
            raise ValueError("Previous stage evidence has no handoff receipt")
        history = workspace / "worker-history" / sha(prior)
        if history.exists():
            raise ValueError("Previous stage evidence was already archived")
        history.parent.mkdir(exist_ok=True)
        evidence.rename(history)
    evidence.mkdir(exist_ok=False)
    seen = set()
    for entry in parent["record_files"]:
        name = entry["path"]
        if name in seen or name == "handoff.json":
            raise ValueError("Duplicate or reserved parent record path")
        seen.add(name)
        source = safe_path(root / "parent-records", name)
        if source.stat().st_size != entry["size"] or sha(source) != entry["sha256"]:
            raise ValueError("Parent record checksum/size mismatch")
        target = safe_path(evidence, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (evidence / "handoff.json").write_text(
        json.dumps(
            {
                "candidate_restored_exactly": True,
                "task_files": expected,
                "parent_input_sha256": parent["input_zip_sha256"],
            },
            indent=2,
        )
        + "\n"
    )
    prepared = root / "prepared-inputs.zip"
    with zipfile.ZipFile(prepared, "x", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(workspace)), (1980, 1, 1, 0, 0, 0))
                with path.open("rb") as source, archive.open(info, "w") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
    return prepared, expected


def main():
    import fsspec

    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    root = Path.cwd()
    spec_path = root / "run-spec.json"
    spec = json.loads(spec_path.read_text())
    parent = unpack_handoff(root, spec)
    prepared, expected = prepare(lambda uri, mode: fsspec.open(uri, mode).open(), root, parent)
    spec["submission_input_zip_sha256"] = spec["input_zip_sha256"]
    spec["input_zip_sha256"] = sha(prepared)
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
    # Checkpoint and read back exact stage inputs before the worker starts.
    for path, name in [(prepared, "inputs.zip"), (spec_path, "run-spec.json")]:
        uri = prefix + "/stage-inputs/" + name
        with path.open("rb") as source, fsspec.open(uri, "wb").open() as destination:
            shutil.copyfileobj(source, destination, 1024 * 1024)
        digest = hashlib.sha256()
        with fsspec.open(uri, "rb").open() as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != sha(path):
            raise ValueError("Stage checkpoint read-back mismatch")
    prepared.replace(root / "inputs.zip")
    print("BIOTASKS_STAGE_INPUT " + json.dumps({"sha256": spec["input_zip_sha256"]}), flush=True)
    result = subprocess.run([sys.executable, "_biotasks_smoke.py"], check=False)
    if spec["stage"] == "review":
        unchanged = task_manifest(root / "workspace") == expected
        receipt = json.dumps({"candidate_unchanged": unchanged})
        with fsspec.open(prefix + "/records/review-integrity.json", "wt").open() as target:
            target.write(receipt)
        print("BIOTASKS_REVIEW_INTEGRITY " + receipt, flush=True)
        if not unchanged:
            raise ValueError("Review worker changed candidate files")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
