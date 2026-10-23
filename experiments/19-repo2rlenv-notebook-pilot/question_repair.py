"""One evidence-grounded question correction; no scientific asset mutations."""

import hashlib
import json
import shutil
from pathlib import Path

from grading_protocol import ContractText, Review, check_review_source_coverage
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
    """Bind an unused repair to original controls and a recorded defect."""
    materialization, grading = Path(materialization), Path(grading)
    candidate, execution = load_materialized(materialization)
    result = read(grading / "result.json")
    if (
        result.get("status") not in {"independent_comparison_unresolved", "public_question_defect"}
        or result.get("cleanup_verified") is not True
        or (grading / "repair.json").exists()
        or (materialization / "question-revision.json").exists()
    ):
        raise ValueError("Question repair needs an unused allowance and verified cleanup")
    if result["status"] == "public_question_defect":
        return semantic_question_context(candidate, execution, grading)
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


def semantic_question_context(candidate, execution, grading):
    defect = read(grading / "public-question-defect.json")
    for name, key in (
        ("candidate.json", "candidate_sha256"),
        ("review.json", "review_sha256"),
        ("question-defect-controls.json", "controls_sha256"),
        ("probes.json", "probes_sha256"),
    ):
        if record(grading / name)["sha256"] != defect[key]:
            raise ValueError("Public-question defect evidence identity changed")
    if defect["quality_repair_used"] is not False:
        raise ValueError("The one quality-repair allowance is already consumed")
    review = Review.model_validate(read(grading / "review.json"))
    check_review_source_coverage(review)
    if (
        review.decision != "revise"
        or review.source_coverage.decision != "approve"
        or not review.question_issues
        or any(
            not i.quote.strip() or i.quote not in candidate["instruction"]
            for i in review.question_issues
        )
    ):
        raise ValueError(
            "Question correction requires source-approved, exact-quoted review evidence"
        )
    grader = read(grading / "candidate.json")
    matches = [
        p
        for p in (grading / "grading/candidates").glob("*/candidate.json")
        if record(p)["sha256"] == defect["candidate_sha256"] and read(p) == grader
    ]
    if len(matches) != 1:
        raise ValueError("Question defect has no unique retained grader candidate")
    controls = read(grading / "question-defect-controls.json")
    basics = [row for row in controls if row["kind"] != "probe"]
    if (
        basics != read(matches[0].parent / "controls.json")
        or not {"reference", "recomputed", "empty", "misplaced", "missing", "alternative"}
        <= {row["kind"] for row in basics}
        or any(row.get("passed_control") is not True for row in basics)
        or any(row["candidate_sha256"] != defect["candidate_sha256"] for row in controls)
    ):
        raise ValueError("Question correction requires original passing basic controls")
    return {
        "materialization_candidate": candidate,
        "materialization_execution": execution,
        "grader_candidate": grader,
        "controls": controls,
        "independent_solution": read(grading / "independent-solution.json"),
        "independent_execution": read(grading / "independent-result.json"),
        "semantic_question_review": review.model_dump(),
        "original_probes": read(grading / "probes.json"),
        "allowed_targets": ["public_question"],
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
