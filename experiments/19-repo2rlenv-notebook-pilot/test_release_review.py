"""Native success cannot bypass final scientific review at release time."""

import copy
import json

import pytest
from release_review import check_final_review
from test_release_probe_evidence import fixture
from test_review_source_coverage import audit
from test_scientific_admission import assessment


def evidence(tmp_path, *, folder="review"):
    fixture(tmp_path, repaired=False)
    candidate = json.loads((tmp_path / "final-candidate.json").read_text())
    admission = assessment()
    for part in [*admission["comparisons"], admission["answer_isolation"]]:
        part["output_paths"] = ["value.txt"]
    review = {
        "decision": "accept_for_packaging",
        "rationale": "Synthetic acceptance evidence",
        "issues": [],
        "source_coverage": audit().model_dump(),
        "scientific_admission": admission,
    }
    controls = json.loads((tmp_path / "final-controls.json").read_text())
    controls[0]["execution"] = {
        "status": "executed",
        "probe_valid_execution": True,
        "grader": {"exit_code": 0},
        "report": {
            "passed": False,
            "checks": [
                {"id": "value", "passed": False, "message": "Wrong value"},
                {"id": "schema", "passed": True, "message": "Valid schema"},
            ],
        },
    }
    root = tmp_path / folder
    (root / "artifact-stage").mkdir(parents=True)
    inputs = {
        "candidate": candidate,
        "artifact_interface": {"output_paths": ["value.txt"]},
        "asset_value_hints": {"findings": []},
    }
    (root / "input.json").write_text(json.dumps(inputs))
    (root / "artifact-stage/artifact.json").write_text(json.dumps({"artifact": review}))
    name = "review-repair.json" if folder.startswith("review-repair") else "review.json"
    (tmp_path / name).write_text(json.dumps(review))
    (tmp_path / "final-controls.json").write_text(json.dumps(controls))
    return candidate, review, inputs, controls


def test_final_submission_can_be_a_later_repair_review(tmp_path):
    evidence(tmp_path, folder="review-repair-003")
    assert check_final_review(tmp_path).decision == "accept_for_packaging"


def test_stale_review_for_another_candidate_cannot_clear_release(tmp_path):
    candidate, _, _, _ = evidence(tmp_path)
    candidate["grader_code"] = "print('a different grader')"
    (tmp_path / "final-candidate.json").write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match="exact candidate"):
        check_final_review(tmp_path)


@pytest.mark.parametrize("defect", ["missing_admission", "unresolved_isolation", "unassessed_hint"])
def test_recorded_acceptance_cannot_override_scientific_defects(tmp_path, defect):
    _, review, inputs, _ = evidence(tmp_path)
    if defect == "missing_admission":
        review.pop("scientific_admission")
    elif defect == "unresolved_isolation":
        review["scientific_admission"]["answer_isolation"].update(
            decision="unresolved", blockers=["Installed answers remain"]
        )
    else:
        inputs["asset_value_hints"]["findings"] = [{"hint_id": "unchecked"}]
    (tmp_path / "review.json").write_text(json.dumps(review))
    (tmp_path / "review/artifact-stage/artifact.json").write_text(json.dumps({"artifact": review}))
    (tmp_path / "review/input.json").write_text(json.dumps(inputs))
    with pytest.raises(ValueError):
        check_final_review(tmp_path)


def test_declared_negative_that_only_breaks_parsing_cannot_clear_release(tmp_path):
    _, _, _, controls = evidence(tmp_path)
    broken = copy.deepcopy(controls)
    broken[0]["execution"]["report"]["checks"][1]["passed"] = False
    (tmp_path / "final-controls.json").write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="executed scientific negative"):
        check_final_review(tmp_path)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "stale_candidate",
        "unassessed_hint",
        "inline_conflict",
        "extra_inline_candidate",
        "missing_document",
        "changed_document",
        "changed_manifest",
        "missing_manifest",
    ],
)
def test_final_packet_review_is_reconstructed_with_original_acceptance_gates(tmp_path, defect):
    import time

    from review_packet import ReviewPacket

    candidate, _, inputs, _ = evidence(tmp_path)
    if defect == "unassessed_hint":
        inputs["asset_value_hints"]["findings"] = [{"hint_id": "unchecked"}]
    value = ReviewPacket(tmp_path / "review-inspection/review-packets", inputs, time.time() + 30)
    model_input = copy.deepcopy(value.model_context)
    if defect == "stale_candidate":
        candidate["grader_code"] = "print('another candidate')"
        (tmp_path / "final-candidate.json").write_text(json.dumps(candidate))
    elif defect == "inline_conflict":
        model_input["artifact_interface"]["output_paths"] = ["another.txt"]
    elif defect == "extra_inline_candidate":
        model_input["candidate"] = inputs["candidate"]
    elif defect in {"missing_document", "changed_document"}:
        document = value.root / value.catalog["candidate"]["path"]
        if defect == "missing_document":
            document.unlink()
        else:
            document.chmod(0o600)
            document.write_text("{}")
    elif defect in {"changed_manifest", "missing_manifest"}:
        manifest = value.root / "manifest.json"
        if defect == "missing_manifest":
            manifest.unlink()
        else:
            manifest.chmod(0o600)
            manifest.write_text("{}")
    (tmp_path / "review/input.json").write_text(json.dumps(model_input))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    if defect:
        with pytest.raises((ValueError, OSError)):
            check_final_review(tmp_path)
    else:
        assert check_final_review(tmp_path).decision == "accept_for_packaging"
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
