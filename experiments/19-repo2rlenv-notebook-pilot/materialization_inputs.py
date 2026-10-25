"""Use recorded derived artifacts as grading inputs, retaining original provenance."""

import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_materialized(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "artifact-manifest.json").read_text())
    recorded = {p["path"]: p for p in manifest["original_small_files"]}
    for name in ("candidate.json", "manifest.json", "result.json"):
        path = directory / name
        expected = recorded[name]
        if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            raise ValueError("Materialized evidence identity changed: " + name)
    candidate = json.loads((directory / "candidate.json").read_text())
    if (directory / "question-revision.json").exists():
        from question_repair import verify_revision

        for name in ("question-revision.json", "instruction.md"):
            if name not in recorded or (
                (directory / name).stat().st_size != recorded[name]["bytes"]
                or sha256(directory / name) != recorded[name]["sha256"]
            ):
                raise ValueError("Question revision identity changed: " + name)
        verify_revision(directory, candidate)
    execution = json.loads((directory / "manifest.json").read_text())
    if candidate.get("environment_review") is not None or "environment" in execution:
        from materialization_environment import effective_exclusions

        environment = execution["environment"]
        # The frozen base is checked separately by each environment consumer;
        # here bind the final review to archived artifacts/catalog and receipt.
        additional = candidate["environment_review"]["additional_exclusions"]
        from materialization_environment import exclusion_key

        added = {exclusion_key(row) for row in additional}
        base = {
            "files": [
                row for row in environment["exclusions"]["files"] if exclusion_key(row) not in added
            ]
        }
        effective_exclusions(base, candidate, execution)
        name = "dependency-assets-final.json"
        catalog = environment["asset_catalog"]
        if (
            name not in recorded
            or (directory / name).is_symlink()
            or (directory / name).stat().st_size != catalog["bytes"]
            or sha256(directory / name) != catalog["sha256"]
            or recorded[name]["sha256"] != catalog["sha256"]
            or recorded[name]["bytes"] != catalog["bytes"]
            or json.loads((directory / name).read_text())["summary"] != environment["asset_summary"]
        ):
            raise ValueError("Final installed-asset catalog identity changed")
    result = json.loads((directory / "result.json").read_text())
    if (
        candidate["disposition"] != "ready"
        or result["status"] != "materialized_requires_scientific_validation"
        or not result["cleanup_verified"]
        or execution["status"] != "executed_requires_scientific_validation"
    ):
        raise ValueError("Successful materialization and cleanup evidence required")
    for key, declared in (
        ("inputs", candidate["input_paths"]),
        ("reference", candidate["output_paths"]),
        ("oracle_outputs", candidate["output_paths"]),
    ):
        for name in declared:
            path = PurePosixPath(name)
            if name in {"", "."} or path.is_absolute() or ".." in path.parts or str(path) != name:
                raise ValueError("Unsafe derived artifact path")
        if len(set(declared)) != len(declared):
            raise ValueError("Duplicate artifact path")
        rows = execution[key]
        if len(rows) != len(declared) or {r["path"] for r in rows} != set(declared):
            raise ValueError("Derived inventory differs from candidate")
    return candidate, execution


def archive_selection(directory):
    _, execution = load_materialized(directory)
    return [
        dict(item, path="grading/materialized/" + kind + "/" + item["path"])
        for kind in ("inputs", "reference", "oracle_outputs")
        for item in execution[kind]
    ]
