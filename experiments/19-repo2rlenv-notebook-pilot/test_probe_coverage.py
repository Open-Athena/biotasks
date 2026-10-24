"""Coverage repair adds challenges while retaining original science and failures."""

import asyncio
import copy
import json
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import grading_remote
import pytest
from grading_protocol import Check, GraderRepair, apply_probe_expectations
from grading_session import GradingSession
from probe_coverage import (
    ProbeSupplement,
    append_supplement,
    prepare_supplement,
    supplement_context,
    unexercised_scientific_checks,
)
from test_probe_expectations import CODE, fixture


def fixture_with_gap():
    candidate, original, correction = fixture()
    original = original.model_copy(update={"probes": [original.probes[0], original.probes[-1]]})
    added = original.probes[0].model_copy(
        update={
            "name": "break-relation",
            "script": "from pathlib import Path\nPath('a.txt').write_text('2')",
            "check_ids": ["agreement"],
            "rationale": "Changing only one value breaks the required equality.",
        }
    )
    supplement = ProbeSupplement(
        disposition="ready", probes=[added], concerns=[], rationale=added.rationale
    )
    return candidate, original, correction, supplement


def negative_record(candidate, original):
    return {
        "kind": "probe",
        "probe": original.probes[0].model_dump(),
        "execution": {
            "status": "executed",
            "probe_valid_execution": True,
            "grader": {"exit_code": 0},
            "report": {
                "passed": False,
                "checks": [
                    {"id": c.id, "passed": c.id != "value", "message": "synthetic observation"}
                    for c in candidate.checks
                ],
            },
        },
    }


def test_executed_coverage_does_not_credit_overdeclared_annotations():
    candidate, original, _, _ = fixture_with_gap()
    record = negative_record(candidate, original)
    before = copy.deepcopy(record)
    assert unexercised_scientific_checks(candidate, [record]) == ["agreement"]
    assert record == before


@pytest.mark.parametrize("parse_passes", [False, True])
def test_parse_failure_cannot_stand_in_for_a_scientific_negative(parse_passes):
    candidate, original, _, _ = fixture_with_gap()
    candidate = candidate.model_copy(
        update={
            "checks": [
                Check(
                    id="parseable",
                    kind="structural",
                    artifacts=["a.txt"],
                    public_requirement="Outputs parse as the declared scientific format.",
                ),
                *candidate.checks,
            ]
        }
    )
    record = negative_record(candidate, original)
    record["execution"]["report"]["checks"][0]["passed"] = parse_passes
    before = copy.deepcopy(record)
    assert unexercised_scientific_checks(candidate, [record]) == (
        ["agreement"] if parse_passes else ["agreement", "value"]
    )
    assert record == before


@pytest.mark.parametrize(
    "change", ["missing", "alternative", "crashed", "no_mutation", "bad_report"]
)
def test_only_completed_scientific_negatives_count(change):
    candidate, original, _, _ = fixture_with_gap()
    record = negative_record(candidate, original)
    if change == "missing":
        record["kind"] = "missing"
    elif change == "alternative":
        record["probe"]["kind"] = "valid_alternative"
    elif change == "crashed":
        record["execution"]["grader"]["exit_code"] = 1
    elif change == "no_mutation":
        record["execution"]["probe_valid_execution"] = False
    else:
        record["execution"]["report"]["checks"] = []
    assert unexercised_scientific_checks(candidate, [record]) == ["agreement", "value"]


def test_append_preserves_all_original_programs_and_does_not_weaken_acceptance():
    candidate, original, correction, supplement = fixture_with_gap()
    before = original.model_dump()
    extended = append_supplement(original, supplement, candidate, ["agreement"])
    assert extended.probes[: len(original.probes)] == original.probes
    assert original.model_dump() == before
    # The exact correction was forbidden when it would remove the only nominal
    # coverage. Appending a real independent challenge permits it without ever
    # changing the original mutation or any scientific criterion.
    repair = GraderRepair(**candidate.model_dump(), probe_expectations=[correction])
    with pytest.raises(ValueError, match="Missing wrong-result"):
        apply_probe_expectations(repair, original)
    repaired, probes = apply_probe_expectations(repair, extended)
    assert repaired == candidate
    assert probes.probes[0].script == original.probes[0].script
    assert probes.probes[-1] == supplement.probes[0]


@pytest.mark.parametrize("change", ["replace", "unknown", "unrelated", "missing_target"])
def test_supplements_cannot_replace_programs_or_invent_coverage(change):
    candidate, original, _, supplement = fixture_with_gap()
    if change == "replace":
        supplement.probes[0].name = original.probes[0].name
    elif change == "unknown":
        supplement.probes[0].check_ids = ["invented"]
    elif change == "unrelated":
        supplement.probes[0].check_ids = ["value", "agreement"]
    else:
        supplement.probes = []
    with pytest.raises(ValueError):
        append_supplement(original, supplement, candidate, ["agreement"])


def test_independent_role_cannot_receive_grader_or_execution_feedback():
    _, original, _, _ = fixture_with_gap()
    allowed = {
        key: {}
        for key in (
            "artifact_interface",
            "public_instruction",
            "checks",
            "paths",
            "output_paths",
            "reference_seconds",
            "verifier_seconds",
        )
    }
    payload = supplement_context(
        allowed | {"grader_code": "private", "controls": "private", "source_evidence": "private"},
        original,
        ["agreement"],
    )
    assert set(payload) == set(allowed) | {"original_probes", "coverage_targets"}
    assert payload["coverage_targets"] == ["agreement"]


@pytest.mark.parametrize("blocked", [False, True])
def test_orchestration_isolates_preflights_and_preserves_originals(tmp_path, blocked):
    candidate, original, _, supplement = fixture_with_gap()
    if blocked:
        supplement = ProbeSupplement(
            disposition="blocked", probes=[], concerns=["No justified edit"], rationale="Blocked"
        )
    context = {
        key: {}
        for key in (
            "artifact_interface",
            "public_instruction",
            "checks",
            "paths",
            "output_paths",
            "reference_seconds",
            "verifier_seconds",
        )
    }
    session = SimpleNamespace(
        command=AsyncMock(return_value={"exit_code": 0}),
        shell=AsyncMock(return_value=json.dumps({"exit_code": 0, "stdout": "isolated\n"})),
        validate_probe_execution=AsyncMock(),
    )

    async def call(schema, name, prompt, inputs, validate, shell):
        assert schema is ProbeSupplement and name == "probe-supplement"
        assert prompt == "notebook-grader-probe-supplement"
        assert inputs["original_probes"] == original.model_dump()
        assert "controls" not in inputs and "grader_code" not in inputs
        await validate(supplement)
        return supplement

    result = asyncio.run(
        prepare_supplement(
            session=session,
            call=call,
            probe_context=context,
            original=original,
            candidate=candidate,
            controls=[negative_record(candidate, original)],
            targets=["agreement"],
            hide_inputs=True,
            root=tmp_path,
        )
    )
    commands = [call.args[0] for call in session.command.await_args_list]
    assert commands == [
        ["rm", "-rf", "/case"],
        ["chmod", "700", "/work/task-inputs"],
        ["chmod", "555", "/work/task-inputs"],
    ]
    assert session.shell.await_args.kwargs["role"] == "probe"
    assert session.validate_probe_execution.await_count == (0 if blocked else 1)
    assert (result is None) is blocked
    assert (tmp_path / "probe-supplement.json").exists()
    assert (tmp_path / "supplemented-probes.json").exists() is not blocked


def test_no_worker_call_or_restore_after_uncertain_isolation_failure(tmp_path):
    candidate, original, _, _ = fixture_with_gap()
    session = SimpleNamespace(
        command=AsyncMock(return_value={"exit_code": 0}),
        shell=AsyncMock(side_effect=TimeoutError("uncertain transport")),
    )
    call = AsyncMock()
    with pytest.raises(TimeoutError):
        asyncio.run(
            prepare_supplement(
                session=session,
                call=call,
                probe_context={},
                original=original,
                candidate=candidate,
                controls=[negative_record(candidate, original)],
                targets=["agreement"],
                hide_inputs=True,
                root=tmp_path,
            )
        )
    call.assert_not_awaited()
    assert session.command.await_count == 2


def test_real_executed_addition_fills_gap_without_changing_correct_grader(
    tmp_path, monkeypatch, capsys
):
    candidate, original, correction, supplement = fixture_with_gap()
    suite = append_supplement(original, supplement, candidate, ["agreement"])
    repaired, suite = apply_probe_expectations(
        GraderRepair(**candidate.model_dump(), probe_expectations=[correction]), suite
    )
    private = tmp_path / "private"
    oracle = private / "oracle"
    oracle.mkdir(parents=True)
    for name in ("a.txt", "b.txt"):
        (oracle / name).write_text("1")
    expected = grading_remote.hashes(oracle)
    (private / "expected.json").write_text(json.dumps(expected))
    (private / "grade.py").write_text(CODE)
    monkeypatch.setattr(grading_remote, "PRIVATE", private)
    monkeypatch.setattr(grading_remote, "CASE", tmp_path / "case")
    monkeypatch.setattr(grading_remote.os, "chown", lambda *args: None)

    def execute(uid, argv, cwd, seconds):
        p = subprocess.run(
            [sys.executable, *argv[1:]], cwd=cwd, capture_output=True, text=True, timeout=seconds
        )
        return {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

    monkeypatch.setattr(grading_remote, "run_as", execute)

    async def upload(source, target):
        shutil.copyfile(source, private / "request.json")

    session = GradingSession(
        remote=SimpleNamespace(upload=upload),
        snapshot={"outputs": [{"path": p} for p in ("a.txt", "b.txt")]},
        root=tmp_path / "session",
        config={"verifier_seconds": 10},
    )
    session.last_candidate = tmp_path / "candidate"
    session.last_candidate.mkdir()
    (session.last_candidate / "candidate.json").write_text(candidate.model_dump_json())

    async def helper(args, seconds, label):
        monkeypatch.setattr(sys, "argv", ["grading_remote.py", "case"])
        grading_remote.main()
        return json.loads(capsys.readouterr().out)

    session.helper = helper
    initial = asyncio.run(session.case(candidate, kind="probe", probe=original.probes[0]))
    assert initial["passed_control"] is False
    assert unexercised_scientific_checks(candidate, [initial]) == ["agreement"]
    fresh = [asyncio.run(session.case(repaired, kind="probe", probe=p)) for p in suite.probes]
    assert all(c["passed_control"] for c in fresh)
    assert unexercised_scientific_checks(repaired, fresh) == []
    assert fresh[0]["probe"]["script"] == initial["probe"]["script"]
    assert candidate == repaired and repaired.grader_code == CODE
    assert grading_remote.hashes(oracle) == expected
    assert initial["passed_control"] is False
