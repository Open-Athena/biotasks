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


def test_restored_reference_selection_and_config():
    config = json.loads((HERE / "grading-config.json").read_text())
    check_config(config)
    items, prefix = selected_outputs(config)
    assert len(items) == 3 and all(p["path"].startswith(prefix) for p in items)
    ast.parse(ISOLATION_PROBE)


@pytest.mark.parametrize(
    "kind,expected", [("reference", True), ("empty", False), ("missing", False), ("probe", False)]
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
    if kind == "probe":
        assert users[0] == remote.PROBE and record["probe_valid_execution"]


def test_probe_blocker_is_representable():
    result = Probes(disposition="blocked", probes=[], concerns=["No valid contract interpretation"])
    assert result.disposition == "blocked"


@pytest.mark.parametrize("repair", [False, True])
def test_orchestration_separates_probe_author_and_gates_acceptance(tmp_path, monkeypatch, repair):
    import grading_session as module

    config = json.loads((HERE / "grading-config.json").read_text())
    calls = []
    c = candidate()
    suite = Probes(
        disposition="ready",
        probes=[probe(), probe(name="format", kind="valid_alternative")],
        concerns=[],
    )

    class Session:
        def __init__(self, **kwargs):
            self.last_controls = []
            self.case_number = 0
            self.frozen_probes = None
            self.frozen_checks = None

        async def initialize(self):
            pass

        async def command(self, *args):
            return {"exit_code": 0}

        async def shell(self, *args, **kwargs):
            return "unused"

        async def validate_candidate(self, value):
            self.last_controls = [{"passed_control": True, "kind": "reference"}]
            self.case_number += 1

        async def case(self, *args, **kwargs):
            self.case_number += 1
            return {"passed_control": True, "kind": "probe"}

    monkeypatch.setattr(module, "GradingSession", Session)

    async def fake_stage(**kwargs):
        name = kwargs["name"]
        inputs = kwargs["context"]
        calls.append(name)
        if name == "probes":
            assert "candidate" not in inputs and "grader_code" not in json.dumps(inputs)
            assert c.grader_code not in json.dumps(inputs)
            assert inputs["public_instruction"] == c.instruction
            value = suite
        elif name.startswith("review"):
            assert inputs["candidate"]["grader_code"] == c.grader_code
            assert len(inputs["controls"]) >= 1
            validator = kwargs["validate"]
            controls = inputs["controls"]
            original = controls[0]["passed_control"]
            controls[0]["passed_control"] = False
            with pytest.raises(ValueError):
                await validator(
                    module.Review(
                        decision="accept_for_packaging", rationale="Cannot accept", issues=[]
                    )
                )
            controls[0]["passed_control"] = original
            value = module.Review(
                decision="revise" if repair and name == "review" else "accept_for_packaging",
                rationale="fixture",
                issues=["repair fixture"] if repair and name == "review" else [],
            )
        else:
            value = c
        if kwargs.get("validate"):
            await kwargs["validate"](value)
        return value

    monkeypatch.setattr(module, "stage", fake_stage)
    result = asyncio.run(
        module.run_grading(
            remote=None,
            snapshot={"directory": HERE / config["reference_directory"]},
            root=tmp_path,
            config=config,
            endpoint="",
            credential="",
            deadline=10**20,
            complete=object(),
        )
    )
    assert calls == ["grader", "probes", "review"] + (["repair", "review-repair"] if repair else [])
    assert result["status"] == "grader_candidate_validated"
    assert not result["harbor_packaging_validated"] and not result["software_portability_validated"]
    assert json.loads((tmp_path / "final-candidate.json").read_text()) == c.model_dump()


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
try:
    grading_remote.run_as(os.getuid(),[{sys.executable!r},'-c',{child!r}],{str(tmp_path)!r},30)
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
