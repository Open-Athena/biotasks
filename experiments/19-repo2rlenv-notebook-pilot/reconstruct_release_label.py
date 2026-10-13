"""Check upstream labels from a separate, reconstructed evidence copy."""

import hashlib
import json
import shutil
import sys
from pathlib import Path, PurePosixPath

from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.quality.labels import label_from_quality, write_labeled_copy
from repo2rlenv.quality.loop.artifacts import parse_task, probe_variant
from repo2rlenv.quality.loop.models import SemanticProbe


def local(root, value):
    if not isinstance(value, str) or not value.startswith("/evidence/"):
        raise ValueError("Expected an absolute evidence path")
    relative = value.removeprefix("/evidence/")
    parts = PurePosixPath(relative)
    if (
        not relative
        or parts.is_absolute()
        or any(x in {".", ".."} for x in relative.split("/"))
        or "\\" in relative
        or "\x00" in relative
    ):
        raise ValueError("Unsafe evidence path")
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Evidence path escapes destination")
    for parent in [target, *target.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Evidence symlinks are not supported")
    return target


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reconstruct(source, dest):
    source, dest = source.resolve(), dest.absolute()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(dest)
    if dest.resolve().is_relative_to(source):
        raise ValueError("Destination must be outside source")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Source evidence contains a symlink")
    original = source / "pilot/quality/result.json"
    q = json.loads(original.read_text())
    local(source, q["task_path"])
    for trial in q["trials"]:
        local(source, trial["result"])
    shutil.copytree(source, dest)

    task = local(dest, q["task_path"])
    q["task_path"] = str(task)
    require(
        inspect_bundle(task)["bundle_hash"] == q["bundle_hash"], "Evidence integrity check failed"
    )
    for t in q["trials"]:
        raw = local(dest, t["result"])
        t["result"] = str(raw)
        require(
            hashlib.sha256(raw.read_bytes()).hexdigest() == t["result_sha256"],
            "Evidence integrity check failed",
        )
        if t["role"] == "probe":
            d = json.loads(raw.read_text())
            variant = (
                raw.parents[4]
                / "probes"
                / raw.parents[2].name
                / Path(d["config"]["task"]["path"]).name
            )
            local(dest, "/evidence/" + variant.relative_to(dest).as_posix())
            require(
                variant.is_relative_to(dest / "pilot/quality/probes"), "Unexpected probe layout"
            )
            if variant.exists():
                shutil.rmtree(variant)  # Only the disposable evidence copy.
            probe_variant(task, SemanticProbe.model_validate(t["probe"]), variant)
            require(
                inspect_bundle(variant)["bundle_hash"] == t["bundle_hash"],
                "Evidence integrity check failed",
            )
            require(
                parse_task(variant).checksum == d["task_checksum"],
                "Evidence integrity check failed",
            )
    result = dest / "quality-local-paths.json"
    result.write_text(json.dumps(q, indent=2))
    label = label_from_quality(task, result)
    require(label.status == "verified", "Evidence integrity check failed")
    labeled = dest / "labeled" / task.name
    write_labeled_copy(task, labeled, label)
    require(
        inspect_bundle(labeled)["bundle_hash"] == q["bundle_hash"],
        "Evidence integrity check failed",
    )
    receipt = {
        "original_quality_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "derived_quality_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
        "bundle_hash": q["bundle_hash"],
        "labeled_task": str(labeled),
        "label_status": label.status,
        "changes": "Local evidence paths and deterministic upstream probe reconstruction only; raw trial bytes unchanged.",
    }
    (dest / "derivation.json").write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    print(json.dumps(reconstruct(Path(sys.argv[1]), Path(sys.argv[2]))))
