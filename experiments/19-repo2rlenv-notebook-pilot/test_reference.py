"""Reference factory checks with synthetic source and scripted model responses."""

import asyncio
import json
import sqlite3
import time

import pytest
from pydantic import ValidationError
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger
from reference_protocol import ReferencePlan, ReferenceReview, materialize
from reference_stage import stage
from run_reference import check_config
from test_design_stage import response


def plan(**changes):
    return ReferencePlan.model_validate(
        {
            "disposition": "prepare",
            "explanation": "Complete synthetic source fixture",
            "environment_rationale": "No external packages",
            "setup_sh": "python -m venv /work/venv",
            "changes": [
                {
                    "purpose": "export",
                    "before": "result = 1\n",
                    "after": "result = 1\nprint(result)\n",
                    "justification": "Expose existing value",
                }
            ],
            "artifacts": [
                {"path": "value.txt", "description": "value", "source_evidence": "result"}
            ],
            "branches": [
                {
                    "name": "value",
                    "scientific_result": "value",
                    "source_evidence": "result",
                    "artifacts": ["value.txt"],
                }
            ],
            "excluded_outputs": [],
            "unresolved_assumptions": [],
            **changes,
        }
    )


def test_export_cannot_replace_source_or_use_ambiguous_anchor():
    prepared = plan()
    script, diff = materialize("result = 1\n", prepared)
    assert script == "result = 1\nprint(result)\n" and "+print(result)" in diff
    with pytest.raises(ValueError, match="unambiguous"):
        materialize("result = 1\nresult = 1\n", prepared)
    prepared.changes[0].after = "result = 2\n"
    with pytest.raises(ValueError, match="not replace"):
        materialize("result = 1\n", prepared)


def test_output_paths_and_coverage_fail_closed():
    with pytest.raises(ValidationError, match="relative"):
        plan(artifacts=[{"path": "../answer", "description": "x", "source_evidence": "x"}])
    with pytest.raises(ValidationError, match="coverage"):
        plan(artifacts=[{"path": "missing-branch.csv", "description": "x", "source_evidence": "x"}])


def test_approval_cannot_keep_a_known_scientific_change():
    with pytest.raises(ValidationError, match="known blockers"):
        ReferenceReview(
            decision="approve",
            rationale="fixture",
            omitted_scientific_results=[],
            scientific_changes=["Changed a threshold"],
            setup_or_export_problems=[],
            checks_for_execution=[],
        )


def test_upstream_revisions_share_the_request_ceiling_and_preserve_prompt(tmp_path):
    requests = []
    invalid = plan().model_dump()
    invalid["branches"][0]["artifacts"] = ["nonexistent.txt"]
    answers = [
        response("submit_artifact", invalid, 1),
        response("revise_artifact", {"patch": {"branches": plan().model_dump()["branches"]}}, 2),
    ]

    async def complete(payload):
        requests.append(payload)
        return answers[len(requests) - 1]

    root = tmp_path / "stage"
    ledger = RequestLedger(tmp_path / "requests.sqlite", {"prepare-0": Allowance(3, 16000)})
    result = asyncio.run(
        stage(
            schema=ReferencePlan,
            name="prepare-0",
            prompt_name="notebook-reference-prepare",
            context={"baseline_script": "result = 1\n"},
            root=root,
            ledger=ledger,
            budget=AuthorBudget(
                RunBudget(
                    BudgetLedger(tmp_path / "budget.sqlite", limit_usd="1"), "reference", "1"
                ),
                tmp_path / "charges",
                "prepare-0",
            ),
            complete=complete,
            deadline=time.time() + 60,
            limits=ChatLimits(),
            max_requests=3,
        )
    )
    assert result.branches[0].artifacts == ["value.txt"]
    assert len(requests) == 2
    assert requests[0]["messages"][0]["content"] == (root / "system-prompt.md").read_text()
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 2
    assert (root / "artifact-stage/draft.json").exists()


def test_request_allocations_cannot_expand_approved_caps():
    from pathlib import Path

    config = json.loads(Path(__file__).with_name("reference-execution.json").read_text())
    check_config(config)
    with pytest.raises(ValueError, match="sum"):
        check_config({**config, "prepare_requests_per_pass": 13})
    with pytest.raises(ValueError, match="envelope"):
        check_config({**config, "reference_seconds": 601})


def test_independent_rejection_prevents_generated_code_execution(tmp_path, monkeypatch):
    import hashlib
    from pathlib import Path
    from types import SimpleNamespace

    import iris_bootstrap
    import run_reference
    from repo2rlenv.execution.base import CommandResult

    config = json.loads(Path(__file__).with_name("reference-execution.json").read_text())
    source = tmp_path / config["source_directory"]
    source.mkdir(parents=True)
    baseline = "result = 1\n"
    (source / "baseline.py").write_text(baseline)
    (source / "conversion.json").write_text(json.dumps({
        "source_sha256": "fixture", "script_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
    }))
    monkeypatch.setattr(run_reference, "__file__", str(tmp_path / "run_reference.py"))
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture")
    commands, events = [], []

    class Sandbox:
        cpu, memory, disk, id, network_block_all = 4, 8, 10, "fixture", False

        def refresh_data(self, **kwargs):
            pass

        def update_network_settings(self, *, network_block_all, **kwargs):
            self.network_block_all = network_block_all

    class Worker:
        def __init__(self, *args):
            pass

        def upload(self, *args):
            pass

        def exec(self, argv, **kwargs):
            commands.append(argv)
            if "-c" in argv:
                return CommandResult(0, json.dumps([{"reachable": True}]))
            if "stage-inputs" in argv:
                return CommandResult(0, '{"files": []}')
            return CommandResult(0, "")

    monkeypatch.setattr(run_reference, "Daytona", lambda: SimpleNamespace(create=lambda *a, **kw: Sandbox()))
    monkeypatch.setattr(run_reference, "DaytonaWorker", Worker)
    monkeypatch.setattr(iris_bootstrap, "export", lambda *a: events.append("durable-export"))

    def cleanup(*args):
        events.append("cleanup")
        return {"passed": True}

    monkeypatch.setattr(run_reference, "cleanup", cleanup)

    async def reviewed(**kwargs):
        if kwargs["schema"] is ReferencePlan:
            return plan()
        return ReferenceReview(decision="reject", rationale="Fixture scientific defect",
                               omitted_scientific_results=[], scientific_changes=["changed method"],
                               setup_or_export_problems=[], checks_for_execution=[])

    monkeypatch.setattr(run_reference, "stage", reviewed)
    result = asyncio.run(run_reference.run(
        config, seed={"source_sha256": "fixture"}, root=tmp_path / "evidence",
        deadline=time.time() + 7200, endpoint="https://model.invalid/v1", credential="fake",
    ))
    assert result["status"] == "review_rejected" and result["cleanup_verified"]
    assert not any("execute" in argv for argv in commands)
    assert events == ["durable-export", "cleanup"]
