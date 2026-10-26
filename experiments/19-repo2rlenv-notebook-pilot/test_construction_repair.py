"""Synthetic ownership, immutable-input and refusal checks; no model or provider."""

import copy
import json

import pytest
from construction_repair import (
    check_candidate,
    check_execution,
    digest,
    load_repair,
    original_candidate,
    repair_context,
    verify_revision,
)
from materialization_protocol import Materialization


def candidate():
    return Materialization(
        disposition="ready",
        instruction="Compute the source analysis and save result.csv.",
        input_paths=["data.csv"],
        output_paths=["result.csv"],
        derive_code="result = analyze(data)\n",
        oracle_code="result = analyze(data)\n",
        rationale="Synthetic original generated task",
        operation_coverage=[
            dict(
                operation_ids=["call-1"],
                role="result",
                artifact_paths=["result.csv"],
                counterpart_id=None,
                rationale="Scientific source endpoint",
            )
        ],
    )


def execution():
    return {
        "status": "executed_requires_scientific_validation",
        "inputs": [{"path": "data.csv", "bytes": 20, "sha256": "a" * 64}],
    }


def record():
    return {
        "kind": "generated_construction_repair_v1",
        "source_context_sha256": digest({"source": "unchanged"}),
        "original_candidate": candidate().model_dump(),
        "original_execution": execution(),
        "blocked_grader": dict(
            disposition="blocked",
            instruction="",
            grader_code="",
            checks=[],
            rationale="Derived reference aliases different entities",
        ),
        "original_records": {},
        "prior_acceptance_reused": False,
    }


def repaired():
    result = candidate().model_dump()
    result["derive_code"] = "result = faithful_export(data)\n"
    return Materialization.model_validate(result)


def test_repair_changes_generated_code_without_reusing_acceptance():
    parent = record()
    assert load_repair(parent, {"source": "unchanged"}) == candidate()
    verify_revision(parent, repaired().model_dump(), execution())
    assert parent == record()


@pytest.mark.parametrize(
    "field", ["instruction", "input_paths", "output_paths", "operation_coverage"]
)
def test_protected_contract_cannot_change(field):
    altered = repaired().model_dump()
    altered[field] = "Different question" if field == "instruction" else []
    # Bypass only schema checks to exercise the semantic guard on empty inventories.
    with pytest.raises(ValueError, match=field):
        check_candidate(candidate(), Materialization.model_construct(**altered))


def test_unchanged_code_cannot_claim_a_repair():
    with pytest.raises(ValueError, match="correct generated code"):
        check_candidate(candidate(), candidate())


@pytest.mark.parametrize(
    "field,value", [("bytes", 21), ("sha256", "b" * 64), ("path", "other.csv")]
)
def test_solver_input_changes_refused(field, value):
    changed = execution()
    changed["inputs"][0][field] = value
    with pytest.raises(ValueError, match="solver-input bytes"):
        check_execution(record(), changed)


def test_duplicate_input_cannot_hide_a_change():
    changed = execution()
    changed["inputs"].append(changed["inputs"][0].copy())
    with pytest.raises(ValueError, match="Duplicate"):
        check_execution(record(), changed)


def test_different_scientific_source_or_policy_cannot_use_feedback():
    with pytest.raises(ValueError, match="different original evidence"):
        load_repair(record(), {"source": "different"})
    altered = record()
    altered["prior_acceptance_reused"] = True
    with pytest.raises(ValueError, match="different original evidence"):
        original_candidate(altered)


def test_removable_answer_exclusions_remain_fixed():
    original = candidate()
    review = dict(
        artifact_inventory_sha256="a" * 64,
        asset_catalog_sha256="b" * 64,
        assessment="Synthetic unchanged environment",
        additional_exclusions=[],
    )
    modified = repaired().model_dump()
    modified["environment_review"] = review
    check_candidate(original, Materialization.model_validate(modified))
    review["additional_exclusions"] = [
        dict(
            distribution="fixture",
            path="fixture/answer.csv",
            sha256="c" * 64,
            reason="A new exclusion",
        )
    ]
    with pytest.raises(ValueError, match="environment exclusions"):
        check_candidate(original, Materialization.model_validate(modified))


@pytest.mark.parametrize(
    "failure", [None, "cleanup", "already_repaired", "different_candidate", "question_revision"]
)
def test_context_binds_original_worker_and_requires_clean_unused_allowance(
    tmp_path, monkeypatch, failure
):
    import construction_repair as module

    raw, materialized, grading = [tmp_path / name for name in ("raw", "view", "grade")]
    for path in (raw / "materialized", raw / "materialize", materialized, grading):
        path.mkdir(parents=True, exist_ok=True)
    original = candidate().model_dump()
    observed = execution()
    monkeypatch.setattr(module, "load_materialized", lambda path: (original, observed))
    files = {
        raw / "materialization-candidate.json": original,
        raw / "materialized/manifest.json": observed,
        raw / "materialize/input.json": {"source": "unchanged"},
        grading / "result.json": {"status": "grader_blocked", "cleanup_verified": True},
        grading / "cleanup.json": {"passed": failure != "cleanup"},
        grading / "candidate.json": record()["blocked_grader"],
    }
    if failure == "different_candidate":
        files[raw / "materialization-candidate.json"] = {**original, "derive_code": "pass"}
    if failure == "already_repaired":
        files[grading / "repair.json"] = {}
    if failure == "question_revision":
        files[materialized / "question-revision.json"] = {}
    for path, value in files.items():
        path.write_text(json.dumps(value))
    before = {p: p.read_bytes() for p in files}
    if failure:
        with pytest.raises(ValueError, match="unused allowance"):
            repair_context(raw, materialized, grading)
    else:
        context = repair_context(raw, materialized, grading)
        assert load_repair(context, {"source": "unchanged"}) == candidate()
        assert context["blocked_grader"] == record()["blocked_grader"]
        assert len(context["original_records"]) == 6
    assert before == {p: p.read_bytes() for p in files}


def test_blocked_repair_never_changes_the_parent():
    old = candidate()
    before = copy.deepcopy(old.model_dump())
    blocked = old.model_copy(update={"disposition": "blocked", "rationale": "Source needs changes"})
    check_candidate(old, blocked)
    assert old.model_dump() == before


@pytest.mark.parametrize(
    "changed", [None, "question", "input", "missing_record", "modified_record"]
)
def test_sealed_repair_survives_native_copy_and_refuses_changed_contract(tmp_path, changed):
    import shutil

    from materialization_inputs import load_materialized
    from run_autonomous import seal_materialization

    raw = tmp_path / "raw"
    bundle = raw / "materialized"
    bundle.mkdir(parents=True)
    revised = repaired().model_dump()
    observed = execution()
    observed["reference"] = [{"path": "result.csv", "bytes": 1, "sha256": "b" * 64}]
    observed["oracle_outputs"] = observed["reference"]
    (bundle / "manifest.json").write_text(json.dumps(observed))
    (raw / "materialization-candidate.json").write_text(json.dumps(revised))
    (raw / "construction-repair.json").write_text(json.dumps(record()))
    (raw / "result.json").write_text(
        json.dumps(
            {"status": "materialized_requires_scientific_validation", "cleanup_verified": True}
        )
    )
    sealed = tmp_path / "sealed"
    seal_materialization(raw, sealed)
    assert load_materialized(sealed)[0] == revised
    native_copy = tmp_path / "native"
    shutil.copytree(sealed, native_copy)
    if changed == "missing_record":
        (native_copy / "construction-revision.json").unlink()
    elif changed == "modified_record":
        (native_copy / "construction-revision.json").write_text("{}")
    elif changed in {"question", "input"}:
        if changed == "question":
            revised["instruction"] = "A different scientific target"
            path = native_copy / "candidate.json"
            path.write_text(json.dumps(revised))
        else:
            observed["inputs"][0]["sha256"] = "c" * 64
            path = native_copy / "manifest.json"
            path.write_text(json.dumps(observed))
        # Even a newly sealed outer identity cannot waive the parent contract.
        manifest = json.loads((native_copy / "artifact-manifest.json").read_text())
        for row in manifest["original_small_files"]:
            if row["path"] == path.name:
                import hashlib

                row.update(
                    bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                )
        (native_copy / "artifact-manifest.json").write_text(json.dumps(manifest))
    if changed:
        with pytest.raises(ValueError, match="revision identity|instruction|solver-input bytes"):
            load_materialized(native_copy)
    else:
        assert load_materialized(native_copy) == load_materialized(sealed)


@pytest.mark.parametrize(
    "conflict",
    [
        None,
        "materialization_directory",
        "independent_repair_file",
        "resume_grading_directory",
        "prior_author_files",
        "allow_quality_repair",
        "materialize_task",
        "absolute_path",
    ],
)
def test_launch_configuration_rejects_incompatible_recovery(conflict):
    from pathlib import Path

    from run_reference_setup import check_config

    config = json.loads((Path(__file__).parent / "reference-setup.json").read_text())
    config.update(
        entrypoint="run_notebook_grader.py",
        materialize_task=True,
        allow_quality_repair=False,
        construction_repair_file="run/repair.json",
        max_tests=None,
        verifier_seconds=120,
    )
    if conflict == "absolute_path":
        config["construction_repair_file"] = "/tmp/repair.json"
    elif conflict == "allow_quality_repair":
        config[conflict] = True
    elif conflict == "materialize_task":
        config[conflict] = False
    elif conflict:
        config[conflict] = "run/other"
    if conflict:
        with pytest.raises(ValueError):
            check_config(config)
    else:
        check_config(config)
