"""Question corrections cannot mutate the reference or gain another repair."""

import hashlib
import json
import shutil

import pytest
from materialization_inputs import load_materialized
from question_repair import read, record, repair_context, revise_question, write


@pytest.fixture
def original(tmp_path):
    directory = tmp_path / "original"
    directory.mkdir()
    candidate = {
        "disposition": "ready",
        "instruction": "Calculate the named measurement using the stated convention.",
        "rationale": "Original rationale",
        "derive_code": "unchanged derivation",
        "oracle_code": "unchanged oracle",
        "input_paths": ["input.dat"],
        "output_paths": ["result.csv"],
    }
    item = {"bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()}
    write(directory / "candidate.json", candidate)
    write(
        directory / "manifest.json",
        {
            "status": "executed_requires_scientific_validation",
            "inputs": [dict(item, path="input.dat")],
            "reference": [dict(item, path="result.csv")],
            "oracle_outputs": [dict(item, path="result.csv")],
        },
    )
    write(
        directory / "result.json",
        {
            "status": "materialized_requires_scientific_validation",
            "cleanup_verified": True,
        },
    )
    (directory / "instruction.md").write_text(candidate["instruction"] + "\n")
    for kind, name in (
        ("inputs", "input.dat"),
        ("reference", "result.csv"),
        ("oracle_outputs", "result.csv"),
    ):
        (directory / kind).mkdir()
        (directory / kind / name).write_bytes(b"1")
    write(
        directory / "artifact-manifest.json",
        {
            "original_small_files": [
                record(path) for path in directory.iterdir() if path.is_file()
            ],
        },
    )
    return directory


def test_question_revision_preserves_science_and_survives_native_copy(original, tmp_path):
    before = {p.relative_to(original): p.read_bytes() for p in original.rglob("*") if p.is_file()}
    destination = tmp_path / "revised"
    revise_question(
        original,
        destination,
        {
            "disposition": "ready",
            "instruction": "Use the source-defined convention.",
            "rationale": "Pinned source establishes the convention.",
        },
    )
    old, old_execution = load_materialized(original)
    new, new_execution = load_materialized(destination)
    assert {**old, "instruction": new["instruction"]} == new
    assert old_execution == new_execution
    for path, raw in before.items():
        assert (original / path).read_bytes() == raw
        if str(path) not in {"candidate.json", "instruction.md", "artifact-manifest.json"}:
            assert (destination / path).read_bytes() == raw
    # A native bundle receives a self-contained view; no sibling-directory dependency.
    native = tmp_path / "native/materialized"
    shutil.copytree(destination, native)
    shutil.rmtree(destination)
    assert load_materialized(native) == (new, new_execution)
    with pytest.raises(ValueError, match="already consumed"):
        revise_question(
            native,
            tmp_path / "twice",
            {
                "disposition": "ready",
                "instruction": "Another correction",
                "rationale": "test",
            },
        )


@pytest.mark.parametrize(
    "mutation",
    ["oracle_code", "derive_code", "output_paths", "reference", "provenance", "instruction"],
)
def test_revision_rejects_scientific_mutation_even_after_resealing(original, tmp_path, mutation):
    destination = tmp_path / "revised"
    revise_question(
        original,
        destination,
        {
            "disposition": "ready",
            "instruction": "Corrected convention",
            "rationale": "test",
        },
    )
    if mutation in {"oracle_code", "derive_code", "output_paths"}:
        candidate = read(destination / "candidate.json")
        candidate[mutation] = ["different.csv"] if mutation == "output_paths" else "different code"
        write(destination / "candidate.json", candidate)
    elif mutation == "reference":
        execution = read(destination / "manifest.json")
        execution["reference"][0]["sha256"] = "0" * 64
        write(destination / "manifest.json", execution)
    elif mutation == "provenance":
        revision = read(destination / "question-revision.json")
        revision["parent_candidate_text"] += " "
        write(destination / "question-revision.json", revision)
    else:
        (destination / "instruction.md").write_text("Unrecorded public question")
    manifest = read(destination / "artifact-manifest.json")
    manifest["original_small_files"] = [
        record(destination / row["path"]) for row in manifest["original_small_files"]
    ]
    write(destination / "artifact-manifest.json", manifest)
    with pytest.raises(ValueError, match="Question repair|Question revision"):
        load_materialized(destination)


@pytest.mark.parametrize("problem", [None, "reference", "cleanup", "used", "unbound"])
def test_only_bound_independent_conflict_can_trigger_repair(original, tmp_path, problem):
    grading = tmp_path / "grading"
    candidate_dir = grading / "grading/candidates/1"
    candidate_dir.mkdir(parents=True)
    write(candidate_dir / "candidate.json", {"grader_code": "frozen comparator"})
    shutil.copyfile(candidate_dir / "candidate.json", grading / "candidate.json")
    digest = record(candidate_dir / "candidate.json")["sha256"]
    controls = [
        {"kind": kind, "passed_control": kind != "alternative", "candidate_sha256": digest}
        for kind in ("reference", "recomputed", "empty", "misplaced", "missing", "alternative")
    ]
    conflict = {"candidate_sha256": digest, "failed_controls": [controls[-1]]}
    if problem == "reference":
        controls[0]["passed_control"] = False
    if problem == "unbound":
        conflict["candidate_sha256"] = "0" * 64
    write(candidate_dir / "controls.json", controls)
    write(grading / "independent-comparison-conflict.json", conflict)
    write(grading / "independent-solution.json", {"code": "original independent code"})
    write(grading / "independent-result.json", {"status": "executed_without_answer_access"})
    write(
        grading / "result.json",
        {
            "status": "independent_comparison_unresolved",
            "cleanup_verified": problem != "cleanup",
        },
    )
    if problem == "used":
        write(grading / "repair.json", {})
    if problem:
        with pytest.raises(ValueError):
            repair_context(original, grading)
    else:
        context = repair_context(original, grading)
        assert context["grader_candidate"] == read(grading / "candidate.json")
        assert context["controls"] == controls


@pytest.mark.parametrize("disposition", ["ready", "blocked"])
def test_worker_returns_only_question_using_recorded_evidence(tmp_path, monkeypatch, disposition):
    import asyncio
    import time

    import run_specification as module

    feedback = {"comparison_conflict": {"reason": "synthetic unit convention conflict"}}
    context = {"revision_context": feedback}
    monkeypatch.setattr(module, "specification_context", lambda *args, **kwargs: context)
    for name, value in (("policy", {}), ("feedback", feedback), ("input", context)):
        write(tmp_path / f"{name}.json", value)
    calls = []

    async def complete(payload):
        calls.append(payload)
        assert json.loads(payload["messages"][1]["content"]) == context
        assert payload["chat_template_kwargs"]["reasoning_effort"] == "high"
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "disposition": disposition,
                                "instruction": "Correct source convention"
                                if disposition == "ready"
                                else "",
                                "rationale": "Source-grounded diagnosis"
                                if disposition == "ready"
                                else "Source itself is broken",
                            }
                        ),
                    },
                }
            ]
        }

    asyncio.run(
        module.run(
            {
                "entrypoint": "run_specification.py",
                "question_repair": True,
                "reference_directory": "unused",
                "policy_file": str(tmp_path / "policy.json"),
                "revision_context_file": str(tmp_path / "feedback.json"),
                "input_file": str(tmp_path / "input.json"),
                "output_format": "json_schema",
                "reasoning_effort": "high",
                "max_requests": 1,
                "request_timeout_seconds": 60,
            },
            root=tmp_path / "worker",
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert len(calls) == 1
    assert read(tmp_path / "worker/question-repair.json")["disposition"] == disposition
    assert not (tmp_path / "worker/specification.json").exists()
