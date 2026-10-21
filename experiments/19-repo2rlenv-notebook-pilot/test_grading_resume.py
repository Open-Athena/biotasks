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


def test_independent_only_recovery_needs_no_grader_but_binds_science_and_program(tmp_path):
    from grading_resume import load_independent

    context = fixture(tmp_path)
    (tmp_path / "candidate.json").unlink()
    assert load_independent(tmp_path, context).code == "pass"
    with pytest.raises(ValueError, match="context differs"):
        load_independent(tmp_path, context | {"question": "different"})
    (tmp_path / "independent-solution.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_independent(tmp_path, context)


def test_unsubmitted_grader_recovery_keeps_independent_code_and_verified_observations(tmp_path):
    from grading_resume import load_grader_draft

    context = fixture(tmp_path)
    manifest = json.loads((tmp_path / "artifact-manifest.json").read_text())
    manifest["original_small_files"] = [
        row for row in manifest["original_small_files"] if row["path"] != "candidate.json"
    ]
    (tmp_path / "candidate.json").unlink()
    name = "grader/artifact-stage/trace.jsonl"
    trace = '{"kind":"tool_result","output":"recorded inspection"}\n'
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_text(trace)
    manifest["original_small_files"].append(
        {
            "path": name,
            "bytes": len(trace.encode()),
            "sha256": hashlib.sha256(trace.encode()).hexdigest(),
        }
    )
    (tmp_path / "artifact-manifest.json").write_text(json.dumps(manifest))
    independent, draft = load_grader_draft(tmp_path, context)
    assert independent.code == "pass"
    assert draft["files"]["inspection-trace.jsonl"] == trace
    with pytest.raises(ValueError, match="artifact unavailable"):
        load_resume(tmp_path, context)
    with pytest.raises(ValueError, match="context differs"):
        load_grader_draft(tmp_path, context | {"question": "changed"})
    path.write_text("changed")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_grader_draft(tmp_path, context)


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


def test_probe_draft_recovery_excludes_grader_feedback_and_binds_original_suite(tmp_path):
    from grading_protocol import Probes
    from grading_resume import load_probe_draft
    from test_grading import probe

    context = fixture(tmp_path)
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )
    values = {
        "probes.json": suite.model_dump(),
        "grading/controls/0007/result.json": {
            "kind": "probe",
            "probe": suite.probes[0].model_dump(),
            "execution": {
                "status": "incomplete",
                "probe_valid_execution": False,
                "probe": {"exit_code": 1, "stderr": "AssertionError"},
                "grader": "PRIVATE-GRADER-FEEDBACK",
                "report": "PRIVATE-GRADER-FEEDBACK",
            },
        },
    }
    manifest = json.loads((tmp_path / "artifact-manifest.json").read_text())
    for name, value in values.items():
        data = json.dumps(value).encode()
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        manifest["original_small_files"].append(
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    (tmp_path / "artifact-manifest.json").write_text(json.dumps(manifest))
    draft = load_probe_draft(tmp_path, context, candidate())
    assert draft["prior_suite"] == suite.model_dump()
    assert draft["execution_failures"][0]["execution"]["probe"]["stderr"] == "AssertionError"
    assert "PRIVATE-GRADER-FEEDBACK" not in json.dumps(draft)
    with pytest.raises(ValueError, match="another grader contract"):
        load_probe_draft(tmp_path, context, candidate().model_copy(update={"rationale": "changed"}))
    with pytest.raises(ValueError, match="context differs"):
        load_probe_draft(tmp_path, context | {"question": "changed"}, candidate())
    (tmp_path / "probes.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_probe_draft(tmp_path, context, candidate())


def test_full_archive_probe_reuse_binds_candidate_bytes_and_cleanup(tmp_path):
    from grading_protocol import Probes
    from grading_resume import load_saved_probes
    from test_grading import probe

    fixture(tmp_path)
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )
    data = suite.model_dump_json().encode()
    (tmp_path / "probes.json").write_bytes(data)
    p = tmp_path / "artifact-manifest.json"
    manifest = json.loads(p.read_text())
    manifest["original_small_files"].append(
        {"path": "probes.json", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    )
    p.write_text(json.dumps(manifest))
    assert load_saved_probes(tmp_path, candidate()) == suite
    with pytest.raises(ValueError, match="different grader contract"):
        load_saved_probes(tmp_path, candidate().model_copy(update={"rationale": "different"}))
    (tmp_path / "probes.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_saved_probes(tmp_path, candidate())
