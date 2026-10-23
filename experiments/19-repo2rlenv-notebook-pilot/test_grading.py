"""Offline contract/control tests; synthetic one-value artifacts, no model or cloud."""

import ast
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from grading_inputs import selected_outputs
from grading_protocol import Grader, Probe, Probes, check_coverage, check_probes, parse_report
from grading_session import ISOLATION_PROBE
from pydantic import ValidationError
from run_reference_setup import check_config

HERE = Path(__file__).parent
CODE = """import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
for k in ('reference-dir','submission-dir','report'):p.add_argument('--'+k,required=True)
a=p.parse_args()
try:
 ok=(Path(a.reference_dir)/'value.txt').read_text()==(Path(a.submission_dir)/'value.txt').read_text()
except OSError:ok=False
Path(a.report).write_text(json.dumps({'passed':ok,'checks':[{'id':'value','passed':ok,'message':'compared value'}]}))
"""


def test_shell_budget_refusal_allows_shorter_request_but_not_transport_retry(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import run_reference_setup
    from grading_session import GradingSession
    from run_reference_setup import Remote

    monkeypatch.setattr(run_reference_setup.time, "time", lambda: 100.0)
    executions = []

    class Worker:
        def upload(self, *args):
            pass

        def exec(self, argv, **kwargs):
            executions.append(argv)
            raise TimeoutError("provider response lost")

    remote = Remote(Worker(), SimpleNamespace(), tmp_path / "remote", 200, 1)
    session = GradingSession(
        remote=remote,
        snapshot={"outputs": []},
        root=tmp_path / "session",
        config={"reference_seconds": 600},
    )

    async def exercise():
        refused = json.loads(await session.shell("true", 600))
        assert refused["status"] == "not_executed"
        assert refused["max_timeout_seconds"] == 75
        assert executions == []
        assert remote.operation == 0 and not remote.uncertain
        # The worker may choose a shorter timeout. A lost response after dispatch
        # must still terminate the session, never become recoverable feedback.
        with pytest.raises(TimeoutError, match="provider response lost"):
            await session.shell("true", 10)
        assert len(executions) == 1 and remote.uncertain
        with pytest.raises(RuntimeError, match="uncertain"):
            await session.shell("true", 10)
        assert len(executions) == 1

    (tmp_path / "remote").mkdir()
    asyncio.run(exercise())


def test_exhausted_shell_budget_is_terminal(tmp_path, monkeypatch):
    import run_reference_setup
    from grading_session import GradingSession
    from run_reference_setup import OperationBudgetExceeded, Remote

    monkeypatch.setattr(run_reference_setup.time, "time", lambda: 100.0)
    remote = Remote(None, None, tmp_path, 120, 1)

    async def upload(*args):
        pass

    remote.upload = upload
    session = GradingSession(
        remote=remote,
        snapshot={"outputs": []},
        root=tmp_path / "session",
        config={"reference_seconds": 600},
    )
    with pytest.raises(OperationBudgetExceeded):
        asyncio.run(session.shell("true", 1))
    assert remote.operation == 0


@pytest.mark.parametrize("available", [1700, 4000])
def test_environment_setup_uses_time_left_and_dispatches_once(tmp_path, monkeypatch, available):
    import hashlib
    from types import SimpleNamespace

    import run_reference_setup
    from grading_session import GradingSession
    from run_reference_setup import Remote

    monkeypatch.setattr(run_reference_setup.time, "time", lambda: 100.0)
    dispatched = []
    log = b"synthetic environment setup completed\n"

    class Worker:
        def upload(self, *args):
            pass

        def exec(self, argv, **kwargs):
            dispatched.append(argv)
            receipt = {
                "argv": json.loads(argv[-4]),
                "timeout_seconds": int(argv[-3]),
                "directory": argv[-2],
                "label": argv[-1],
                "exit_code": 0,
                "timed_out": False,
                "log_sha256": hashlib.sha256(log).hexdigest(),
            }
            return SimpleNamespace(stdout=json.dumps(receipt), checked=lambda *args: None)

        def download(self, path, target):
            assert path.endswith(".log")
            target.write_bytes(log)

    remote = Remote(Worker(), SimpleNamespace(), tmp_path / "remote", 100 + 15 + available, 1)
    config = {"setup_seconds": 1800, "reference_seconds": 600, "verifier_seconds": 120}
    session = GradingSession(
        remote=remote, snapshot={"outputs": []}, root=tmp_path / "session", config=config
    )
    reply = asyncio.run(session.build_environment())
    expected = 1645 if available == 1700 else 1800
    assert reply["exit_code"] == 0 and reply["timeout_seconds"] == expected
    assert len(dispatched) == remote.operation == 1 and not remote.uncertain
    record = json.loads((tmp_path / "remote/operations/0001/operation.json").read_text())
    assert (
        record["seconds"] == expected and record["reconciliation_deadline"] <= remote.deadline - 15
    )
    assert config == {"setup_seconds": 1800, "reference_seconds": 600, "verifier_seconds": 120}
    admission = tmp_path / "session/setup-admission.json"
    assert admission.exists() == (available == 1700)
    if admission.exists():
        record = json.loads(admission.read_text())
        assert record["initial_command_dispatched"] is False
        assert record["effective_timeout_seconds"] == expected
        assert record["return_allowance_seconds"] == 55
        assert record["campaign_deadline_extended"] is False


def test_environment_setup_does_not_retry_uncertain_dispatch(tmp_path):
    from grading_session import GradingSession

    attempts = []

    class Remote:
        async def command(self, *args):
            attempts.append(args)
            raise TimeoutError("dispatched command outcome unknown")

    session = GradingSession(
        remote=Remote(),
        snapshot={"outputs": []},
        root=tmp_path / "session",
        config={"setup_seconds": 1800},
    )
    with pytest.raises(TimeoutError, match="outcome unknown"):
        asyncio.run(session.build_environment())
    assert len(attempts) == 1
    assert not (tmp_path / "session/setup-admission.json").exists()


def test_environment_setup_requires_time_for_existing_return_margin(tmp_path, monkeypatch):
    import run_reference_setup
    from grading_session import GradingSession
    from run_reference_setup import OperationBudgetExceeded, Remote

    monkeypatch.setattr(run_reference_setup.time, "time", lambda: 100.0)
    remote = Remote(None, None, tmp_path / "remote", 170, 1)
    session = GradingSession(
        remote=remote,
        snapshot={"outputs": []},
        root=tmp_path / "session",
        config={"setup_seconds": 1800},
    )
    with pytest.raises(OperationBudgetExceeded):
        asyncio.run(session.build_environment())
    assert remote.operation == 0 and not remote.uncertain


def test_grader_author_can_inspect_before_candidate_submission(tmp_path):
    from grading_session import GradingSession

    async def helper(argv, timeout, label):
        assert argv == ["shell", "author", "inspect recorded format", "12"]
        assert timeout == 22
        return {"exit_code": 0, "stdout": "recorded format evidence"}

    session = GradingSession(
        remote=None,
        snapshot={"outputs": []},
        root=tmp_path / "session",
        config={"reference_seconds": 600},
    )
    session.helper = helper
    result = json.loads(asyncio.run(session.shell("inspect recorded format", 12)))
    assert result["stdout"] == "recorded format evidence"
    assert session.candidate_number == 0


def candidate():
    return Grader(
        disposition="ready",
        instruction="Return the reference value",
        grader_code=CODE,
        checks=[
            {
                "id": "value",
                "kind": "scientific",
                "artifacts": ["value.txt"],
                "public_requirement": "Equal value",
            }
        ],
        rationale="Synthetic controller fixture",
    )


def probe(**changes):
    d = dict(
        name="wrong-value",
        kind="wrong_solution",
        focus="general",
        rationale="Change value",
        evidence=[{"path": "instruction.md", "quote": "value"}],
        script="from pathlib import Path\nPath('value.txt').write_text('wrong')",
        check_ids=["value"],
    )
    return Probe(**(d | changes))


def test_reports_cannot_skip_checks_or_lie_about_reward():
    c = candidate()
    valid = {"passed": False, "checks": [{"id": "value", "passed": False, "message": "wrong"}]}
    assert parse_report(valid, c) == valid
    for invalid in (
        {"passed": True, "checks": []},
        valid | {"passed": True},
        valid | {"checks": valid["checks"] * 2},
        valid | {"passed": 0},
    ):
        with pytest.raises(ValueError):
            parse_report(invalid, c)


def test_scientific_coverage_and_independent_probe_coverage():
    c = candidate()
    check_coverage(c, ["value.txt"])
    with pytest.raises(ValueError):
        check_coverage(c, ["value.txt", "other.txt"])
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )
    check_probes(suite, c)
    with pytest.raises(ValueError):
        check_probes(
            suite.model_copy(update={"probes": [probe(name="format", kind="valid_alternative")]}), c
        )


def test_bad_code_is_recoverable_schema_feedback():
    with pytest.raises(ValidationError):
        Grader.model_validate(candidate().model_dump() | {"grader_code": "def invalid("})
    with pytest.raises(ValidationError):
        probe(script="def invalid(")
    assert (
        Grader(
            disposition="blocked",
            instruction="",
            grader_code="",
            checks=[],
            rationale="Missing evidence",
        ).disposition
        == "blocked"
    )


def test_restored_reference_selection_and_config(tmp_path, monkeypatch):
    import grading_inputs

    config = json.loads((HERE / "grading-config.json").read_text())
    check_config(config)
    monkeypatch.setattr(grading_inputs, "HERE", tmp_path)
    original = tmp_path / "original"
    replay = tmp_path / "replay"
    original.mkdir()
    replay.mkdir()
    prefix = "reference-replay/replay/trials/1/outputs/"
    item = {"path": "value.txt", "bytes": 1, "sha256": "recorded-digest"}
    (original / "artifact-manifest.json").write_text(json.dumps({"large_outputs": [item]}))
    path = replay / "artifact-manifest.json"
    path.write_text(json.dumps({"large_outputs": [item | {"path": prefix + item["path"]}]}))
    (replay / "result.json").write_text(
        json.dumps(
            {
                "all_outputs_byte_identical_to_original": True,
                "cleanup_verified": True,
            }
        )
    )
    selection = {"reference_directory": "original", "replay_directory": "replay"}
    items, actual_prefix = selected_outputs(selection)
    assert actual_prefix == prefix
    assert items == [item | {"path": prefix + "value.txt"}]
    changed = json.loads(path.read_text())
    changed["large_outputs"][0]["bytes"] += 1
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="identities disagree"):
        selected_outputs(selection)
    ast.parse(ISOLATION_PROBE)


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("reference", True),
        ("empty", False),
        ("missing", False),
        ("misplaced", False),
        ("probe", False),
    ],
)
def test_remote_case_runs_real_synthetic_grader_without_changing_oracle(
    tmp_path, monkeypatch, capsys, kind, expected
):
    import grading_remote as remote

    private = tmp_path / "private"
    oracle = private / "oracle"
    oracle.mkdir(parents=True)
    (oracle / "value.txt").write_text("right")
    expected_hashes = remote.hashes(oracle)
    (private / "expected.json").write_text(json.dumps(expected_hashes))
    (private / "grade.py").write_text(CODE)
    request = {"kind": kind, "seconds": 10}
    if kind == "missing":
        request["omit"] = "value.txt"
    if kind == "probe":
        request["script"] = probe().script
    (private / "request.json").write_text(json.dumps(request))
    monkeypatch.setattr(remote, "PRIVATE", private)
    monkeypatch.setattr(remote, "CASE", tmp_path / "case")
    monkeypatch.setattr(remote.os, "chown", lambda *a: None)
    users = []

    def execute(uid, argv, cwd, seconds):
        users.append(uid)
        argv = [sys.executable, *argv[1:]]
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=seconds)
        return {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

    monkeypatch.setattr(remote, "run_as", execute)
    monkeypatch.setattr(sys, "argv", ["grading_remote.py", "case"])
    remote.main()
    record = json.loads(capsys.readouterr().out)
    assert record["status"] == "executed" and record["report"]["passed"] is expected
    assert remote.hashes(oracle) == expected_hashes
    assert users[-1] == remote.GRADER
    if kind == "misplaced":
        assert record["submission_before"] == {"outputs/value.txt": expected_hashes["value.txt"]}
    if kind == "probe":
        assert users[0] == remote.PROBE and record["probe_valid_execution"]


def test_probe_blocker_is_representable():
    result = Probes(disposition="blocked", probes=[], concerns=["No valid contract interpretation"])
    assert result.disposition == "blocked"


def test_misplaced_control_exposes_an_output_root_fallback(tmp_path, monkeypatch):
    """Correct values in a second outputs/ layer are still at undeclared paths."""
    import grading_remote as remote
    from grading_session import GradingSession

    private = tmp_path / "private"
    (private / "oracle").mkdir(parents=True)
    (private / "oracle/value.txt").write_text("right")
    monkeypatch.setattr(remote, "PRIVATE", private)
    monkeypatch.setattr(remote, "CASE", tmp_path / "case")
    remote.prepare("misplaced")
    # A plausible but incorrect grader searches another outputs/ directory.
    code = CODE.replace(
        "Path(a.submission_dir)/'value.txt'",
        "next(p for p in (Path(a.submission_dir)/'value.txt', "
        "Path(a.submission_dir)/'outputs/value.txt') if p.is_file())",
    )
    program, report = tmp_path / "grade.py", tmp_path / "report.json"
    program.write_text(code)
    process = subprocess.run(
        [
            sys.executable,
            str(program),
            "--reference-dir",
            str(remote.CASE / "reference"),
            "--submission-dir",
            str(remote.CASE / "submission"),
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    observed = parse_report(json.loads(report.read_text()), candidate())
    assert observed["passed"] is True  # The executable counterexample succeeds.

    class Transport:
        async def upload(self, *args):
            pass

    session = GradingSession(
        remote=Transport(),
        snapshot={"outputs": [{"path": "value.txt"}]},
        root=tmp_path / "session",
        config={"verifier_seconds": 10},
    )
    session.last_candidate = tmp_path / "candidate"
    session.last_candidate.mkdir()
    (session.last_candidate / "candidate.json").write_text(json.dumps(candidate().model_dump()))

    async def executed(*args):
        return {
            "status": "executed",
            "grader": {"exit_code": process.returncode},
            "report": observed,
        }

    session.helper = executed
    control = asyncio.run(session.case(candidate(), kind="misplaced"))
    assert control["passed_control"] is False


@pytest.mark.parametrize("mode", ["probe-check", "case"])
@pytest.mark.parametrize(
    "script,mutated",
    [
        ("from pathlib import Path; Path('value.txt').rename('elsewhere.txt')", True),
        ("from pathlib import Path; Path('value.txt').unlink()", True),
        ("pass", False),
        ("from pathlib import Path; Path('value.txt').unlink(); raise RuntimeError()", False),
    ],
)
def test_probe_preflight_separates_mutation_from_acceptance(
    tmp_path, monkeypatch, capsys, mode, script, mutated
):
    import grading_remote as remote

    private = tmp_path / "private"
    oracle = private / "oracle"
    oracle.mkdir(parents=True)
    (oracle / "value.txt").write_text("right")
    expected = remote.hashes(oracle)
    (private / "expected.json").write_text(json.dumps(expected))
    (private / "grade.py").write_text(CODE)
    (private / "request.json").write_text(
        json.dumps({"kind": "probe", "seconds": 10, "script": script})
    )
    monkeypatch.setattr(remote, "PRIVATE", private)
    monkeypatch.setattr(remote, "CASE", tmp_path / "case")
    monkeypatch.setattr(remote.os, "chown", lambda *a: None)
    users = []

    def execute(uid, argv, cwd, seconds):
        users.append(uid)
        result = subprocess.run(
            [sys.executable, *argv[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=seconds,
        )
        return dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    monkeypatch.setattr(remote, "run_as", execute)
    monkeypatch.setattr(sys, "argv", ["grading_remote.py", mode])
    remote.main()
    result = json.loads(capsys.readouterr().out)
    assert result["probe_valid_execution"] is mutated
    assert remote.hashes(oracle) == expected
    if mode == "case" and mutated:
        assert users == [remote.PROBE, remote.GRADER]
        assert result["status"] == "executed"
        assert result["report"]["passed"] is False
    else:
        assert users == [remote.PROBE]
        assert "report" not in result
        assert result["status"] == ("probe_executed" if mutated else "incomplete")


@pytest.mark.parametrize("comparison_conflict", [False, True])
@pytest.mark.parametrize("repair", [False, True])
@pytest.mark.parametrize(
    "derived,resume,reuse_probes,contract_only",
    [
        (False, False, False, False),
        (True, False, False, False),
        (True, True, False, False),
        (True, "draft", False, False),
        (True, "independent", False, False),
        (True, "probe-draft", False, False),
        (True, True, True, False),
        (True, True, True, True),
        (True, "frozen", False, False),
    ],
)
def test_orchestration_separates_probe_author_and_gates_acceptance(
    tmp_path,
    monkeypatch,
    repair,
    derived,
    resume,
    reuse_probes,
    contract_only,
    comparison_conflict,
    semantic_feedback=False,
    independent_repair=False,
    inspect_review=False,
    question_defect=False,
):
    import grading_session as module

    config = json.loads((HERE / "grading-config.json").read_text())
    config.pop("resume_grading_directory", None)
    config.pop("resume_grader_draft_directory", None)
    config.pop("resume_independent_directory", None)
    config.pop("resume_probes_directory", None)
    config.pop("resume_probe_draft_directory", None)
    config.pop("resume_contract_directory", None)
    config.pop("contract_feedback_file", None)
    config["inspect_review_evidence"] = inspect_review
    frozen_grader = resume == "frozen"
    if frozen_grader:
        resume = False
        config["allow_quality_repair"] = False
    if resume:
        import grading_resume

        recovery_key = {
            "draft": "resume_grader_draft_directory",
            "independent": "resume_independent_directory",
        }.get(resume, "resume_grading_directory")
        config[recovery_key] = "saved-run"

        def reuse(directory, context):
            assert "independent_solution" not in context
            independent = module.AlternativeSolution(
                disposition="ready", code="pass", rationale="fixture"
            )
            if resume == "independent":
                return independent
            return independent, (
                {"files": {"inspection-trace.jsonl": "private-grader-observations"}}
                if resume == "draft"
                else candidate()
            )

        monkeypatch.setattr(
            grading_resume,
            {"draft": "load_grader_draft", "independent": "load_independent"}.get(
                resume, "load_resume"
            ),
            reuse,
        )
    calls = []
    commands = []
    c = candidate()
    if frozen_grader:
        config["frozen_grader_file"] = str(tmp_path / "frozen-grader-input.json")
        (tmp_path / "frozen-grader-input.json").write_text(
            json.dumps(
                {
                    "materialization_candidate": {
                        "instruction": "Scientific question",
                        "input_paths": ["input.txt"],
                        "oracle_code": "private-original-oracle",
                    },
                    "grader_candidate": c.model_dump(),
                }
            )
        )
        if independent_repair:
            frozen_record = json.loads((tmp_path / "frozen-grader-input.json").read_text())
            config["independent_repair_file"] = str(tmp_path / "independent-repair.json")
            (tmp_path / "independent-repair.json").write_text(
                json.dumps(
                    {
                        **frozen_record,
                        "prior_code": "pass",
                        "issues": [
                            {
                                "public_requirement_quote": "Scientific question",
                                "prior_code_quote": "pass",
                            }
                        ],
                    }
                )
            )
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )

    if resume == "probe-draft":
        config["resume_probe_draft_directory"] = "saved-run"
        monkeypatch.setattr(
            grading_resume, "load_probe_draft", lambda *args: {"prior_suite": suite.model_dump()}
        )

    if reuse_probes:
        config["resume_probes_directory"] = "saved-probes"
        monkeypatch.setattr(grading_resume, "load_saved_probes", lambda directory, candidate: suite)

    if contract_only:
        config["resume_contract_directory"] = "saved-contract"
        feedback = tmp_path / "feedback.md"
        feedback.write_text("Explain limits accurately")
        config["contract_feedback_file"] = str(feedback)
        monkeypatch.setattr(grading_resume, "load_contract_base", lambda *args: c)

    effective_repair = repair and not contract_only and not frozen_grader
    conflict_on = (2 if effective_repair else 1) if comparison_conflict else None

    class Session:
        def __init__(self, **kwargs):
            self.independent_conflict = None
            self.validation_count = 0
            self.last_controls = []
            self.case_number = 0
            self.frozen_probes = None
            self.frozen_checks = None
            self.paths = ["value.txt"]
            self.remote = self

        async def upload(self, *args):
            pass

        async def download(self, remote, local):
            local.write_bytes(b"1")

        async def initialize(self):
            pass

        async def command(self, *args):
            commands.append(args[0])
            import hashlib

            return {
                "exit_code": 0,
                "log": json.dumps(
                    {
                        "status": "executed_without_answer_access",
                        "outputs": [
                            {
                                "path": "value.txt",
                                "bytes": 1,
                                "sha256": hashlib.sha256(b"1").hexdigest(),
                            }
                        ],
                    }
                ),
            }

        async def shell(self, *args, **kwargs):
            return json.dumps({"exit_code": 0, "stdout": "isolated"})

        async def validate_candidate(self, value):
            self.last_controls = [{"passed_control": True, "kind": "reference"}]
            self.case_number += 1
            self.validation_count += 1
            if self.validation_count == conflict_on:
                self.independent_conflict = {"fixture": "unresolved independent output"}

        async def validate_probe_execution(self, value):
            assert value in suite.probes

        async def case(self, *args, **kwargs):
            self.case_number += 1
            return {"passed_control": True, "kind": "probe"}

    monkeypatch.setattr(module, "GradingSession", Session)

    repair_input_summaries = []
    repair_reviews = []
    review_roots = []
    review_charge_operations = []

    async def fake_stage(**kwargs):
        name = kwargs["name"]
        inputs = kwargs["context"]
        calls.append(name)
        if inspect_review and name in {"review", "review-repair"}:
            assert "package_inspection" in inputs and "reference_inspection" in inputs
            assert "shell" not in kwargs or kwargs["shell"] is None
            response = json.loads(
                await kwargs["extra_handlers"]["read_reference_file"](path="value.txt")
            )
            assert response["lines"] == [{"line": 1, "text": "1"}]
            assert "read_reference_file" in [
                item["function"]["name"] for item in kwargs["extra_tools"]
            ]
        else:
            assert not kwargs.get("extra_tools") and not kwargs.get("extra_handlers")
            assert "reference_inspection" not in inputs and "package_inspection" not in inputs
        if name != "independent":
            assert inputs["artifact_interface"] == module.artifact_interface(["value.txt"])
        if derived and name not in {"independent", "probes"}:
            assert inputs["specification"] == {"task_brief": "Scientific question"}
            assert "operator_handoff" not in inputs
            assert "repeatability" in inputs and "source_evidence" in inputs
        if name == "contract":
            assert kwargs["shell"] is None
            assert inputs["candidate"] == c.model_dump()
            value = module.ContractText(
                disposition="ready", instruction=c.instruction, rationale=c.rationale
            )
        elif name == "independent":
            assert "private-original-oracle" not in json.dumps(inputs)
            assert "source_evidence" not in inputs and "materialization" not in inputs
            assert inputs["public_instruction"] == "Scientific question"
            if independent_repair:
                assert inputs["repair"] == {
                    "prior_code": "pass",
                    "issues": [
                        {
                            "public_requirement_quote": "Scientific question",
                            "prior_code_quote": "pass",
                        }
                    ],
                }
                assert "grader_candidate" not in json.dumps(inputs)
            else:
                assert "repair" not in inputs
            value = module.AlternativeSolution(
                disposition="ready", code="pass", rationale="fixture"
            )
        elif name == "probes":
            if resume == "probe-draft":
                assert kwargs["shell"] is None
                assert inputs["prior_probe_draft"]["prior_suite"] == suite.model_dump()
            else:
                assert "prior_probe_draft" not in inputs
            assert "prior_worker_draft" not in inputs
            assert "private-grader-observations" not in json.dumps(inputs)
            assert "candidate" not in inputs and "grader_code" not in json.dumps(inputs)
            assert c.grader_code not in json.dumps(inputs)
            assert inputs["public_instruction"].endswith(c.instruction)
            assert "source_evidence" not in inputs
            assert ["find", "/work/probe", "-mindepth", "1", "-delete"] in commands
            assert "materialization" not in inputs
            assert "independent_solution" not in inputs
            assert "task_inputs" not in inputs["paths"]
            if derived:
                assert commands[-1] == ["chmod", "700", "/work/task-inputs"]
            value = suite
        elif name.startswith("review"):
            review_roots.append(kwargs["root"])
            operation = kwargs["budget"].reserve(0.001, "Synthetic review response")
            kwargs["budget"].settle(operation, 0)
            review_charge_operations.append(operation)
            assert inputs["control_summary"] == module.control_summary(inputs["controls"])
            assert "inputs/original.py" in inputs["source_evidence"]
            assert "inputs/plan.json" in inputs["source_evidence"]
            source_coverage = {
                "decision": "approve",
                "rationale": "Synthetic source coverage fixture",
                "omitted_scientific_endpoints": [],
                "unsupported_evidence_claims": [],
                "scientific_scope_changes": [],
                "remaining_validation": [],
            }
            assert inputs["initial_probes"] == suite.model_dump()
            if name == "review-repair":
                repair_reviews.append(inputs["candidate"])
                assert inputs["author_input_control_summary"] == repair_input_summaries[-1]
                assert inputs["author_input_control_summary"] != inputs["control_summary"]
                assert inputs["probes"]["concerns"] == ["Updated synthetic concern"]
                assert inputs["initial_probes"]["concerns"] == suite.concerns
                assert (
                    inputs["probes"]["probes"][0]["rationale"]
                    == "Correction justified by the unchanged public rule"
                )
                assert inputs["probes"]["probes"][0]["script"] == suite.probes[0].script
            if derived:
                assert ["chmod", "555", "/work/task-inputs"] in commands
            assert inputs["candidate"]["grader_code"] == c.grader_code
            assert len(inputs["controls"]) >= 1
            validator = kwargs["validate"]
            controls = inputs["controls"]
            original = controls[0]["passed_control"]
            controls[0]["passed_control"] = False
            with pytest.raises(ValueError):
                await validator(
                    module.Review(
                        decision="accept_for_packaging",
                        rationale="Cannot accept",
                        issues=[],
                        source_coverage=source_coverage,
                        question_issues=[],
                    )
                )
            controls[0]["passed_control"] = original
            with pytest.raises(ValueError, match="unresolved issues"):
                await validator(
                    module.Review(
                        decision="accept_for_packaging",
                        rationale="Cannot excuse a substantive defect",
                        issues=["An acceptance boundary is not publicly defined"],
                        source_coverage=source_coverage,
                        question_issues=[],
                    )
                )
            semantic_rejection = (
                semantic_feedback and name == "review-repair" and len(repair_reviews) == 1
            )
            value = module.Review(
                decision="blocked"
                if semantic_rejection and semantic_feedback == "blocked"
                else "revise"
                if (repair and name == "review") or semantic_rejection or question_defect
                else "accept_for_packaging",
                rationale="fixture",
                issues=["Unsupported calibration claim"]
                if semantic_rejection
                else ["repair fixture"]
                if repair and name == "review"
                else [],
                source_coverage=source_coverage,
                question_issues=[
                    {
                        "quote": "Scientific question",
                        "evidence": "Recorded toy source contradicts this claim",
                    }
                ]
                if question_defect
                else [],
            )
        else:
            if name == "repair":
                assert inputs["control_summary"] == module.control_summary(inputs["controls"])
                repair_input_summaries.append(json.loads(json.dumps(inputs["control_summary"])))
            if name == "grader" and resume == "draft":
                assert kwargs["shell"] is None
                assert "private-grader-observations" in json.dumps(inputs["prior_worker_draft"])
            if name == "grader" and resume == "independent":
                assert callable(kwargs["shell"])
                assert "prior_worker_draft" not in inputs
                assert ["python", "/work/alternative_remote.py"] in commands
                receipt = json.loads((tmp_path / "resume.json").read_text())
                assert receipt["reexecute_independent"] and not receipt["prior_acceptance_reused"]
            value = (
                module.GraderRepairSubmission(
                    **c.model_dump(exclude={"checks"}),
                    probe_concerns=["Updated synthetic concern"],
                    probe_expectations=[
                        {
                            "name": suite.probes[0].name,
                            "check_ids": suite.probes[0].check_ids,
                            "rationale": "Correction justified by the unchanged public rule",
                        }
                    ],
                )
                if name == "repair"
                else c
            )
        if kwargs.get("validate"):
            if name == "repair" and semantic_feedback:
                with pytest.raises(ValueError, match="Unsupported calibration claim"):
                    await kwargs["validate"](value)
                # Executable success must not finalize a semantically rejected
                # submission. The same repair worker receives the feedback and
                # submits a corrected explanation, with science unchanged.
                assert not (tmp_path / "final-candidate.json").exists()
                if semantic_feedback == "blocked":
                    value.disposition = "blocked"
                    value.rationale = "Scientific evidence requires work outside this repair"
                else:
                    value.rationale = "Supported comparison; no unsupported measurement claim"
            await kwargs["validate"](value)
        return value

    monkeypatch.setattr(module, "stage", fake_stage)
    inspection_snapshot = {"hashes": {}}
    if inspect_review:
        import hashlib

        outputs = tmp_path / "original-outputs"
        outputs.mkdir()
        (outputs / "value.txt").write_bytes(b"1")
        reference = HERE / config["reference_directory"]
        inspection_snapshot = {
            "hashes": {
                name: hashlib.sha256((reference / name).read_bytes()).hexdigest()
                for name in ("trial/uv.lock", "trial/environment.txt")
            },
            "restored_outputs_root": str(outputs),
            "outputs": [
                {"path": "value.txt", "bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()}
            ],
        }
    result = asyncio.run(
        module.run_grading(
            remote=None,
            snapshot={
                "directory": HERE / config["reference_directory"],
                **inspection_snapshot,
                **(
                    {
                        "materialization": {
                            "candidate": {
                                "instruction": "Scientific question",
                                "input_paths": ["input.txt"],
                                "oracle_code": "private-original-oracle",
                            },
                            "execution": {},
                        }
                    }
                    if derived
                    else {}
                ),
            },
            root=tmp_path,
            config=config,
            endpoint="",
            credential="",
            deadline=10**20,
            complete=object(),
        )
    )
    if question_defect:
        assert result["status"] == "public_question_defect"
        assert calls == ["independent", "grader", "probes", "review"]
        assert (tmp_path / "public-question-defect.json").is_file()
        assert not (tmp_path / "repair.json").exists()
        return
    if semantic_feedback == "blocked":
        assert result["status"] == "repair_blocked"
        assert not result.get("final_controls_passed", False)
        assert not (tmp_path / "final-candidate.json").exists()
        assert calls == ["independent", "grader", "probes", "review", "repair", "review-repair"]
        assert len(repair_reviews) == 1
        return
    if comparison_conflict:
        initial = (
            ["contract"]
            if contract_only
            else (
                ["grader"]
                if resume in {"draft", "independent"}
                else []
                if resume
                else (["independent"] if derived else []) + ["grader"]
            )
        )
        expected = initial
        if frozen_grader:
            expected = ["independent"]
        if conflict_on == 2:
            expected += ([] if reuse_probes else ["probes"]) + ["review", "repair"]
        assert calls == expected
        assert result["status"] == "independent_comparison_unresolved"
        assert not result["final_controls_passed"] and not result["harbor_packaging_validated"]
        assert not (tmp_path / "final-candidate.json").exists()
        assert json.loads((tmp_path / "independent-comparison-conflict.json").read_text()) == {
            "fixture": "unresolved independent output"
        }
        return
    expected = (
        (
            ["contract"]
            if contract_only
            else (
                ["grader"]
                if resume in {"draft", "independent"}
                else []
                if resume
                else (["independent"] if derived else []) + ["grader"]
            )
        )
        + ([] if reuse_probes else ["probes"])
        + ["review"]
        + (["repair", "review-repair"] if effective_repair else [])
    )
    if frozen_grader:
        expected = ["independent", "probes", "review"]
        assert json.loads((tmp_path / "candidate.json").read_text()) == c.model_dump()
        assert not (tmp_path / "repair.json").exists()
    if semantic_feedback:
        expected.append("review-repair")
        assert len(repair_reviews) == 2
        assert len(set(review_roots)) == len(review_roots) == 3
        assert len(set(review_charge_operations)) == len(review_charge_operations) == 3
        assert len(list((tmp_path / "charges").glob("*/1.json"))) == 3
        assert repair_reviews[0]["rationale"] != repair_reviews[1]["rationale"]
        for field in ("checks", "grader_code", "instruction"):
            assert repair_reviews[0][field] == repair_reviews[1][field]
        records = sorted((tmp_path / "repair-submission-reviews").glob("*.json"))
        assert [json.loads(p.read_text())["review"]["decision"] for p in records] == [
            "revise",
            "accept_for_packaging",
        ]
    assert calls == expected
    assert result["status"] == (
        "grader_requires_further_work"
        if (contract_only or frozen_grader) and repair
        else "grader_candidate_validated"
    )
    assert not result["harbor_packaging_validated"] and not result["software_portability_validated"]
    expected_candidate = c.model_dump()
    if semantic_feedback:
        expected_candidate["rationale"] = "Supported comparison; no unsupported measurement claim"
    assert json.loads((tmp_path / "final-candidate.json").read_text()) == expected_candidate


@pytest.mark.parametrize("semantic_feedback", [True, "blocked"])
def test_semantic_rejection_returns_to_existing_repair_worker(
    tmp_path, monkeypatch, semantic_feedback
):
    test_orchestration_separates_probe_author_and_gates_acceptance(
        tmp_path,
        monkeypatch,
        repair=True,
        derived=True,
        resume=False,
        reuse_probes=False,
        contract_only=False,
        comparison_conflict=False,
        semantic_feedback=semantic_feedback,
    )


def test_independent_repair_uses_fresh_isolated_author_and_frozen_grader(tmp_path, monkeypatch):
    test_orchestration_separates_probe_author_and_gates_acceptance(
        tmp_path,
        monkeypatch,
        repair=False,
        derived=True,
        resume="frozen",
        reuse_probes=False,
        contract_only=False,
        comparison_conflict=False,
        independent_repair=True,
    )


def test_outer_termination_reaps_generated_process_group(tmp_path):
    import os
    import signal
    import time

    pid_file = tmp_path / "child-pid"
    child = (
        "import os,time;from pathlib import Path;Path("
        + repr(str(pid_file))
        + ").write_text(str(os.getpid()));time.sleep(30)"
    )
    wrapper = f"""
import sys,os
sys.path.insert(0,{str(HERE)!r})
import grading_remote
os.setgroups=lambda _:None
os.setgid=lambda _:None
os.setuid=lambda _:None
# This local process cannot allocate sandbox UIDs. The original process-group
# assertion remains real; the separate tests cover dedicated-role discovery.
os.geteuid=lambda:0
grading_remote.stop_role_processes=lambda _:None
try:
    grading_remote.run_as(grading_remote.AUTHOR,[{sys.executable!r},'-c',{child!r}],{str(tmp_path)!r},30)
except TimeoutError:
    print('interrupted-and-reaped')
"""
    process = subprocess.Popen(
        [sys.executable, "-c", wrapper], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    child_pid = None
    try:
        until = time.monotonic() + 5
        while (
            not pid_file.exists() or not pid_file.read_text().strip()
        ) and time.monotonic() < until:
            time.sleep(0.01)
        assert pid_file.exists(), "synthetic child did not start"
        child_pid = int(pid_file.read_text())
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        assert stdout.strip() == "interrupted-and-reaped"
        with pytest.raises(ProcessLookupError):
            os.killpg(child_pid, 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
        if child_pid is not None:
            try:
                os.killpg(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("failed_kinds", [set(), {"alternative"}, {"reference", "alternative"}])
def test_independent_mismatch_halts_without_rewriting_grader(tmp_path, failed_kinds):
    from grading_session import GradingSession

    class Remote:
        async def upload(self, *args):
            pass

    session = GradingSession(
        remote=Remote(),
        snapshot={"outputs": [{"path": "value.txt"}]},
        root=tmp_path / "session",
        config={},
    )
    session.alternative_executed = True

    async def case(value, *, kind, **kwargs):
        return {"kind": kind, "passed_control": kind not in failed_kinds}

    session.case = case
    original = candidate().model_dump()
    if "reference" in failed_kinds:
        with pytest.raises(ValueError, match="Executable control failures"):
            asyncio.run(session.validate_candidate(candidate()))
        assert session.independent_conflict is None
    else:
        asyncio.run(session.validate_candidate(candidate()))
        if "alternative" in failed_kinds:
            assert session.independent_conflict is not None
            assert [r["kind"] for r in session.independent_conflict["failed_controls"]] == [
                "alternative"
            ]
        else:
            assert session.independent_conflict is None
    # Controller classification must preserve the actual submitted science/code.
    saved = session.root / "candidates/1/candidate.json"
    assert json.loads(saved.read_text()) == original
    assert (saved.parent / "grade.py").read_text() == original["grader_code"] + "\n"
