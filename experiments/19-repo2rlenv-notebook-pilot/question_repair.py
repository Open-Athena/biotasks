"""One evidence-grounded question correction; no scientific asset mutations."""

import hashlib
import json
import shutil
from pathlib import Path

from grading_protocol import ContractText
from materialization_inputs import load_materialized
from repo2rlenv.quality.loop.models import Edit


def read(path):
    return json.loads(Path(path).read_text())


def record(path):
    raw = path.read_bytes()
    return {"path": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def repair_context(materialization, grading):
    """Only the first, cleaned-up, otherwise passing independent conflict qualifies."""
    materialization, grading = Path(materialization), Path(grading)
    candidate, execution = load_materialized(materialization)
    result = read(grading / "result.json")
    if (
        result.get("status") != "independent_comparison_unresolved"
        or result.get("cleanup_verified") is not True
        or (grading / "repair.json").exists()
        or (materialization / "question-revision.json").exists()
    ):
        raise ValueError("Question repair needs an unused allowance and verified cleanup")
    conflict = read(grading / "independent-comparison-conflict.json")
    grader = read(grading / "candidate.json")
    matches = [
        path
        for path in (grading / "grading/candidates").glob("*/candidate.json")
        if record(path)["sha256"] == conflict["candidate_sha256"] and read(path) == grader
    ]
    if len(matches) != 1:
        raise ValueError("Comparison conflict has no unique retained grader candidate")
    controls = read(matches[0].parent / "controls.json")
    kinds = {row["kind"] for row in controls}
    failures = [row for row in controls if row.get("passed_control") is not True]
    if (
        not {"reference", "recomputed", "empty", "misplaced", "missing", "alternative"} <= kinds
        or not failures
        or failures != conflict["failed_controls"]
        or any(row["kind"] != "alternative" for row in failures)
        or any(row["candidate_sha256"] != conflict["candidate_sha256"] for row in controls)
    ):
        raise ValueError("Question repair requires passing reference and all other basic controls")
    return {
        "materialization_candidate": candidate,
        "materialization_execution": execution,
        "grader_candidate": grader,
        "controls": controls,
        "independent_solution": read(grading / "independent-solution.json"),
        "independent_execution": read(grading / "independent-result.json"),
        "comparison_conflict": conflict,
    }


def revise_question(original, destination, response):
    """Seal a derived question view, retaining byte-identical scientific assets."""
    original, destination = Path(original), Path(destination)
    candidate, _ = load_materialized(original)
    response = ContractText.model_validate(response)
    if response.disposition != "ready" or response.instruction == candidate["instruction"]:
        raise ValueError("Question repair must supply a ready, changed question")
    if (original / "question-revision.json").exists():
        raise ValueError("The one quality-repair allowance is already consumed")
    shutil.copytree(original, destination)
    edit = Edit(
        path="instruction.md",
        old=candidate["instruction"],
        new=response.instruction,
        executable=False,
    )
    provenance = {
        "kind": "question_only_no_scientific_reexecution_claimed",
        "parent_candidate_text": (original / "candidate.json").read_text(),
        "parent_artifact_manifest": read(original / "artifact-manifest.json"),
        "edit": edit.model_dump(),
        "rationale": response.rationale,
    }
    write(destination / "question-revision.json", provenance)
    write(destination / "candidate.json", {**candidate, "instruction": response.instruction})
    (destination / "instruction.md").write_text(response.instruction + "\n")
    manifest = read(destination / "artifact-manifest.json")
    replacements = {"candidate.json", "instruction.md", "question-revision.json"}
    manifest["original_small_files"] = [
        row for row in manifest["original_small_files"] if row["path"] not in replacements
    ] + [record(destination / name) for name in sorted(replacements)]
    write(destination / "artifact-manifest.json", manifest)
    load_materialized(destination)


def verify_revision(directory, candidate):
    """Check the parent candidate and executed inventories, including after native copy."""
    directory = Path(directory)
    revision = read(directory / "question-revision.json")
    old_text = revision["parent_candidate_text"]
    old = json.loads(old_text)
    parent = {
        row["path"]: row for row in revision["parent_artifact_manifest"]["original_small_files"]
    }
    if record_bytes(old_text.encode()) != (
        parent["candidate.json"]["bytes"],
        parent["candidate.json"]["sha256"],
    ):
        raise ValueError("Question revision parent identity changed")
    edit = Edit.model_validate(revision["edit"])
    if (
        revision["kind"] != "question_only_no_scientific_reexecution_claimed"
        or edit.path != "instruction.md"
        or edit.old != old["instruction"]
        or edit.new != candidate["instruction"]
        or edit.new == edit.old
        or edit.executable
        or candidate != {**old, "instruction": edit.new}
        or (directory / "instruction.md").read_text() != edit.new + "\n"
    ):
        raise ValueError("Question repair changed a scientific asset")
    for name in ("manifest.json", "result.json"):
        if record(directory / name) != parent[name]:
            raise ValueError("Question repair changed executed evidence")


def record_bytes(raw):
    return len(raw), hashlib.sha256(raw).hexdigest()
