"""Return a blocked generated reference to its owner without changing the task."""

import hashlib
import json
from pathlib import Path

from grading_protocol import Grader
from materialization_inputs import load_materialized
from materialization_protocol import Materialization


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def input_identity(execution):
    """Only exact original solver-input bytes are admissible after this repair."""
    rows = execution["inputs"]
    result = {}
    for row in rows:
        if row["path"] in result:
            raise ValueError("Duplicate task input in construction repair")
        result[row["path"]] = {key: row[key] for key in ("bytes", "sha256")}
    return result


def repair_context(raw, materialization, grading):
    """Use original blocked-worker evidence only; no operator diagnosis or edits."""
    raw, materialization, grading = map(Path, (raw, materialization, grading))
    candidate, execution = load_materialized(materialization)
    result = read(grading / "result.json")
    cleanup = read(grading / "cleanup.json")
    grader = Grader.model_validate(read(grading / "candidate.json"))
    if (
        result.get("status") != "grader_blocked"
        or result.get("cleanup_verified") is not True
        or cleanup.get("passed") is not True
        or cleanup.get("remaining")
        or cleanup.get("creation_uncertain")
        or grader.disposition != "blocked"
        or (grading / "repair.json").exists()
        or (materialization / "question-revision.json").exists()
        or (raw / "construction-repair.json").exists()
        or read(raw / "materialization-candidate.json") != candidate
        or read(raw / "materialized/manifest.json") != execution
    ):
        raise ValueError(
            "Construction repair needs an unused allowance and cleaned blocked grading"
        )
    source_context = read(raw / "materialize/input.json")
    if "construction_repair" in source_context or "prior_worker_draft" in source_context:
        raise ValueError("Only an original autonomous construction can use this repair")
    originals = {
        "construction_candidate": raw / "materialization-candidate.json",
        "construction_execution": raw / "materialized/manifest.json",
        "construction_input": raw / "materialize/input.json",
        "grading_result": grading / "result.json",
        "grading_cleanup": grading / "cleanup.json",
        "blocked_grader": grading / "candidate.json",
    }
    return {
        "kind": "generated_construction_repair_v1",
        "source_context_sha256": digest(source_context),
        "original_candidate": candidate,
        "original_execution": execution,
        "blocked_grader": grader.model_dump(),
        "original_records": {
            key: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for key, p in originals.items()
        },
        "prior_acceptance_reused": False,
    }


def original_candidate(record):
    if (
        set(record)
        != {
            "kind",
            "source_context_sha256",
            "original_candidate",
            "original_execution",
            "blocked_grader",
            "original_records",
            "prior_acceptance_reused",
        }
        or record["kind"] != "generated_construction_repair_v1"
        or record["prior_acceptance_reused"] is not False
        or Grader.model_validate(record["blocked_grader"]).disposition != "blocked"
    ):
        raise ValueError("Construction repair belongs to different original evidence")
    original = Materialization.model_validate(record["original_candidate"])
    execution = record["original_execution"]
    if (
        original.disposition != "ready"
        or execution["status"] != "executed_requires_scientific_validation"
        or set(input_identity(execution)) != set(original.input_paths)
    ):
        raise ValueError("Construction repair requires an executed original task")
    return original


def load_repair(record, context):
    original = original_candidate(record)
    if record["source_context_sha256"] != digest(context):
        raise ValueError("Construction repair belongs to different original evidence")
    return original


def check_candidate(original, candidate):
    if candidate.disposition == "blocked":
        return
    for key in ("instruction", "input_paths", "output_paths", "operation_coverage"):
        if getattr(candidate, key) != getattr(original, key):
            raise ValueError("Construction repair cannot change " + key)
    if (candidate.derive_code, candidate.oracle_code) == (
        original.derive_code,
        original.oracle_code,
    ):
        raise ValueError("Construction repair must correct generated code or decline")
    if candidate.environment_review is not None:
        if candidate.environment_review.additional_exclusions != exclusions(original):
            raise ValueError("Construction repair cannot change the environment exclusions")


def exclusions(original):
    return original.environment_review.additional_exclusions if original.environment_review else []


def check_execution(record, execution):
    if input_identity(execution) != input_identity(record["original_execution"]):
        raise ValueError("Construction repair changed solver-input bytes; refuse this candidate")


def verify_revision(record, candidate, execution):
    check_candidate(original_candidate(record), Materialization.model_validate(candidate))
    check_execution(record, execution)


async def stage_inputs(session, record, directory):
    """Make existing task inputs available without rerunning their derivation."""
    directory = Path(directory)
    candidate, execution = load_materialized(directory)
    if candidate != record["original_candidate"] or execution != record["original_execution"]:
        raise ValueError("Construction repair input handoff belongs to another task")
    files = []
    for item in execution["inputs"]:
        path = directory / "inputs" / item["path"]
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Linked construction repair input")
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if sha != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Construction repair input bytes changed before staging")
        files.append((path, item["path"]))
    remote = "/work/construction-repair-inputs"
    for path, name in files:
        reply = await session.command(
            ["mkdir", "-p", str(Path(remote, name).parent)], 30, "construction-repair-input-parent"
        )
        if reply["exit_code"]:
            raise RuntimeError("Cannot stage original construction inputs")
        await session.remote.upload(path, remote + "/" + name)
    reply = await session.command(
        ["chmod", "-R", "a+rX,a-w", remote], 30, "seal-construction-repair-inputs"
    )
    if reply["exit_code"]:
        raise RuntimeError("Cannot freeze original construction inputs")
    return remote
