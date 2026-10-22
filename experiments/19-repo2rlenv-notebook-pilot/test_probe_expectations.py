"""Repair annotations while preserving executable challenges and coverage."""

import asyncio
import json
import shutil
import subprocess
import sys
from types import SimpleNamespace

import grading_remote
import pytest
from grading_protocol import Grader, GraderRepair, Probes, apply_probe_expectations, control_summary
from grading_session import GradingSession
from pydantic import ValidationError

CODE = """import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
for key in ('reference-dir','submission-dir','report'):p.add_argument('--'+key,required=True)
a=p.parse_args()
ref=Path(a.reference_dir);sub=Path(a.submission_dir)
values=[float((sub/name).read_text()) for name in ('a.txt','b.txt')]
correct=all(value==float((ref/name).read_text()) for value,name in zip(values,('a.txt','b.txt')))
checks=[{'id':'value','passed':correct,'message':'reference values'},
        {'id':'agreement','passed':values[0]==values[1],'message':'internal agreement'}]
Path(a.report).write_text(json.dumps({'passed':all(c['passed'] for c in checks),'checks':checks}))
"""


def fixture():
    grader = Grader(
        disposition="ready",
        instruction="Return the reference values in a.txt and b.txt; they must agree.",
        grader_code=CODE,
        checks=[
            {
                "id": name,
                "kind": "scientific",
                "artifacts": ["a.txt", "b.txt"],
                "public_requirement": requirement,
            }
            for name, requirement in [("value", "Reference values"), ("agreement", "Equal values")]
        ],
        rationale="Synthetic two-file scientific comparison fixture",
    )
    probes = []
    for name, kind, script, ids in [
        (
            "paired-edit",
            "wrong_solution",
            "for name in ('a.txt','b.txt'): Path(name).write_text('99')",
            ["value", "agreement"],
        ),
        ("one-edit", "wrong_solution", "Path('a.txt').write_text('2')", ["agreement"]),
        ("format", "valid_alternative", "Path('a.txt').write_text('1.0')", ["value"]),
    ]:
        probes.append(
            dict(
                name=name,
                kind=kind,
                focus="general",
                rationale="Synthetic mutation",
                evidence=[{"path": "instruction.md", "quote": "values"}],
                script="from pathlib import Path\n" + script,
                check_ids=ids,
            )
        )
    suite = Probes(disposition="ready", probes=probes, concerns=[])
    update = dict(
        name="paired-edit",
        check_ids=["value"],
        rationale="Paired wrong values violate reference comparison but preserve internal equality.",
    )
    return grader, suite, update


def test_annotations_cannot_change_mutations_or_original_records():
    grader, original, update = fixture()
    before = original.model_dump()
    repaired, revised = apply_probe_expectations(
        GraderRepair(**grader.model_dump(), probe_expectations=[update]), original
    )
    assert repaired == grader and original.model_dump() == before
    for old, new in zip(original.probes, revised.probes, strict=True):
        assert old.model_dump(exclude={"check_ids", "rationale"}) == new.model_dump(
            exclude={"check_ids", "rationale"}
        )
    assert revised.probes[0].check_ids == ["value"]
    assert revised.probes[1:] == original.probes[1:]


@pytest.mark.parametrize(
    "replacement", [None, [], ["Controller evidence corrects the earlier note."]]
)
def test_suite_annotation_repair_keeps_original_and_every_mutation(replacement):
    grader, original, update = fixture()
    original = original.model_copy(update={"concerns": ["An earlier, unverified annotation."]})
    before = original.model_dump()
    repaired, revised = apply_probe_expectations(
        GraderRepair(
            **grader.model_dump(), probe_expectations=[update], probe_concerns=replacement
        ),
        original,
    )
    assert repaired == grader and original.model_dump() == before
    assert revised.concerns == (original.concerns if replacement is None else replacement)
    for old, new in zip(original.probes, revised.probes, strict=True):
        assert old.model_dump(exclude={"check_ids", "rationale"}) == new.model_dump(
            exclude={"check_ids", "rationale"}
        )


def test_summary_counts_expected_control_outcomes_instead_of_positive_rewards():
    controls = [
        {"kind": "reference", "passed_control": True, "execution": {"report": {"passed": True}}},
        {"kind": "empty", "passed_control": True, "execution": {"report": {"passed": False}}},
        {"kind": "probe", "passed_control": True, "probe": {"kind": "wrong_solution"}},
        {"kind": "probe", "passed_control": False, "probe": {"kind": "valid_alternative"}},
    ]
    assert control_summary(controls) == {
        "controls": 4,
        "expected_outcomes_met": 3,
        "by_kind": {"empty": 1, "probe": 2, "reference": 1},
        "probes_by_kind": {"valid_alternative": 1, "wrong_solution": 1},
    }
    assert control_summary([])["controls"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"name": "missing"},
        {"check_ids": ["unknown"]},
        {"check_ids": ["value", "value"]},
        {"name": "format", "check_ids": ["agreement"]},
    ],
)
def test_invalid_or_coverage_removing_updates_are_rejected(change):
    grader, original, update = fixture()
    with pytest.raises(ValueError):
        apply_probe_expectations(
            GraderRepair(**grader.model_dump(), probe_expectations=[update | change]), original
        )


def test_repairs_cannot_drop_scientific_probe_coverage():
    grader, original, update = fixture()
    with pytest.raises(ValueError, match="Missing wrong-result controls"):
        apply_probe_expectations(
            GraderRepair(
                **grader.model_dump(), probe_expectations=[update, update | {"name": "one-edit"}]
            ),
            original,
        )


def test_scripts_and_kinds_are_not_fields_of_an_annotation_update():
    grader, original, update = fixture()
    for field in ("script", "kind", "focus", "evidence"):
        with pytest.raises(ValidationError):
            GraderRepair(**grader.model_dump(), probe_expectations=[update | {field: "changed"}])
    with pytest.raises(ValueError, match="Duplicate"):
        apply_probe_expectations(
            GraderRepair(**grader.model_dump(), probe_expectations=[update, update]), original
        )


def test_real_wrong_submission_still_fails_after_annotation_correction(
    tmp_path, monkeypatch, capsys
):
    grader, original, update = fixture()
    _, revised = apply_probe_expectations(
        GraderRepair(**grader.model_dump(), probe_expectations=[update]), original
    )
    private = tmp_path / "private"
    oracle = private / "oracle"
    oracle.mkdir(parents=True)
    for name in ("a.txt", "b.txt"):
        (oracle / name).write_text("1")
    reference_hashes = grading_remote.hashes(oracle)
    (private / "expected.json").write_text(json.dumps(reference_hashes))
    (private / "grade.py").write_text(CODE)
    monkeypatch.setattr(grading_remote, "PRIVATE", private)
    monkeypatch.setattr(grading_remote, "CASE", tmp_path / "case")
    monkeypatch.setattr(grading_remote.os, "chown", lambda *args: None)

    def execute(uid, argv, cwd, seconds):
        result = subprocess.run(
            [sys.executable, *argv[1:]], cwd=cwd, capture_output=True, text=True, timeout=seconds
        )
        return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

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
    (session.last_candidate / "candidate.json").write_text(grader.model_dump_json())

    async def helper(args, seconds, label):
        monkeypatch.setattr(sys, "argv", ["grading_remote.py", "case"])
        grading_remote.main()
        return json.loads(capsys.readouterr().out)

    session.helper = helper
    first = asyncio.run(session.case(grader, kind="probe", probe=original.probes[0]))
    second = asyncio.run(session.case(grader, kind="probe", probe=revised.probes[0]))
    assert first["passed_control"] is False and second["passed_control"] is True
    for record in (first, second):
        assert record["execution"]["report"]["passed"] is False
        assert record["execution"]["grader"]["exit_code"] == 0
        assert record["probe"]["script"] == original.probes[0].script
    assert (session.root / "controls/0001/result.json").is_file()
    assert (session.root / "controls/0002/result.json").is_file()
    assert grading_remote.hashes(oracle) == reference_hashes


@pytest.mark.parametrize("disposition", ["ready", "blocked"])
def test_repair_submission_cannot_reauthor_frozen_requirements(disposition):
    from grading_protocol import GraderRepairSubmission, bind_repair_checks

    grader, _, _ = fixture()
    original = grader.model_dump()
    editable = grader.model_dump(exclude={"checks"})
    editable["disposition"] = disposition
    editable["rationale"] = "Repair the implementation under the unchanged public rules"
    submission = GraderRepairSubmission.model_validate(editable)
    bound = bind_repair_checks(submission, grader.checks)
    assert bound.checks == grader.checks
    assert bound.model_dump()["checks"] == original["checks"]
    assert "checks" not in GraderRepairSubmission.model_json_schema()["properties"]
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GraderRepairSubmission.model_validate({**editable, "checks": original["checks"]})
    # The archived representation remains backward compatible and independent.
    assert GraderRepair.model_validate(bound.model_dump()) == bound
    bound.checks[0].public_requirement = "Attempt to weaken the copied definition"
    assert grader.model_dump() == original


def test_binding_repair_still_rejects_invalid_ready_grader_code():
    from grading_protocol import GraderRepairSubmission, bind_repair_checks

    grader, _, _ = fixture()
    submission = GraderRepairSubmission.model_validate(
        {**grader.model_dump(exclude={"checks"}), "grader_code": "def broken(:"}
    )
    with pytest.raises(ValidationError):
        bind_repair_checks(submission, grader.checks)
