"""Recovery rejects changed science or bytes before executing saved worker code."""

import hashlib
import json

import pytest
from grading_resume import load_resume
from test_grading import candidate


def fixture(root):
    context = {"paths": {"reference_outputs": "/reference"}, "question": "synthetic"}
    saved = context | {
        "paths": context["paths"] | {"independent_outputs": "/alternative"},
        "independent_solution": {},
        "independent_execution": {},
    }
    values = {
        "result.json": {"cleanup_verified": True, "status": "incomplete"},
        "grader/input.json": saved,
        "independent-solution.json": {
            "disposition": "ready",
            "code": "pass",
            "rationale": "fixture",
        },
        "candidate.json": candidate().model_dump(),
    }
    records = []
    for name, value in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value).encode()
        path.write_bytes(data)
        records.append(
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    (root / "artifact-manifest.json").write_text(
        json.dumps({"download_checked": True, "original_small_files": records})
    )
    return context


def test_resume_returns_original_code_and_rejects_changed_inputs(tmp_path):
    context = fixture(tmp_path)
    independent, grader = load_resume(tmp_path, context)
    assert independent.code == "pass"
    assert grader == candidate()
    with pytest.raises(ValueError, match="context differs"):
        load_resume(tmp_path, context | {"question": "changed"})
    (tmp_path / "candidate.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_resume(tmp_path, context)


def test_resume_requires_verified_download(tmp_path):
    context = fixture(tmp_path)
    p = tmp_path / "artifact-manifest.json"
    value = json.loads(p.read_text())
    value["download_checked"] = False
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="download-verified"):
        load_resume(tmp_path, context)


def test_partial_probe_recovery_binds_bytes_contract_and_cleanup(tmp_path):
    from grading_protocol import Probes
    from grading_resume import load_saved_probes
    from test_grading import probe

    c = candidate()
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )
    records = []
    for name, value in {
        "grading/candidate.json": c.model_dump(),
        "grading/probes.json": suite.model_dump(),
    }.items():
        p = tmp_path / name
        p.parent.mkdir(exist_ok=True)
        data = json.dumps(value).encode()
        p.write_bytes(data)
        records.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    (tmp_path / "manifest.json").write_text(json.dumps(records))
    (tmp_path / "host-stop.json").write_text(json.dumps({"state": "KILLED"}))
    cleanup = tmp_path / "provider-cleanup.json"
    cleanup.write_text(json.dumps({"complete": True, "sandboxes": []}))
    assert load_saved_probes(tmp_path, c) == suite
    with pytest.raises(ValueError, match="different grader"):
        load_saved_probes(tmp_path, c.model_copy(update={"instruction": "changed"}))
    cleanup.write_text(json.dumps({"complete": True, "sandboxes": ["live"]}))
    with pytest.raises(ValueError, match="teardown"):
        load_saved_probes(tmp_path, c)
    cleanup.write_text(json.dumps({"complete": True, "sandboxes": []}))
    (tmp_path / "grading/probes.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_saved_probes(tmp_path, c)


def test_contract_text_cannot_change_executable_fields():
    from grading_protocol import ContractText, apply_contract_text

    c = candidate()
    revised = apply_contract_text(
        c, ContractText(disposition="ready", instruction="Clear rules", rationale="Corrected prose")
    )
    assert revised.grader_code == c.grader_code and revised.checks == c.checks
    assert revised.instruction == "Clear rules"
    with pytest.raises(ValueError, match="blocked"):
        apply_contract_text(
            c,
            ContractText(
                disposition="blocked", instruction="", rationale="Needs scientific change"
            ),
        )


def test_contract_base_binds_verified_revision_to_originals(tmp_path):
    from grading_protocol import Probes
    from grading_resume import load_contract_base
    from test_grading import probe

    original = candidate()
    final = original.model_copy(update={"grader_code": "pass # repaired"})
    probes = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )
    final_bytes = json.dumps(final.model_dump()).encode()
    values = {
        "candidate.json": original.model_dump(),
        "probes.json": probes.model_dump(),
        "final-candidate.json": final.model_dump(),
        "result.json": {"cleanup_verified": True, "final_controls_passed": True},
        "final-controls.json": [
            {"passed_control": True, "candidate_sha256": hashlib.sha256(final_bytes).hexdigest()}
        ],
    }
    records = []
    for name, value in values.items():
        data = json.dumps(value).encode()
        (tmp_path / name).write_bytes(data)
        records.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    (tmp_path / "artifact-manifest.json").write_text(
        json.dumps({"download_checked": True, "original_small_files": records})
    )
    assert load_contract_base(tmp_path, original, probes) == final
    with pytest.raises(ValueError, match="different original"):
        load_contract_base(tmp_path, original.model_copy(update={"instruction": "changed"}), probes)
    (tmp_path / "final-candidate.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_contract_base(tmp_path, original, probes)
