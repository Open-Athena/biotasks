"""Reference factory checks with synthetic source and scripted model responses."""

import asyncio
import json
import sqlite3
import time

import pytest
from pydantic import ValidationError
from reference_protocol import ReferencePlan, ReferenceReview, materialize
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget
from run_reference import check_config
from test_design_stage import response

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


def plan(**changes):
    return ReferencePlan.model_validate(
        {
            "disposition": "prepare",
            "explanation": "Complete synthetic source fixture",
            "environment_rationale": "No external packages",
            "pyproject_toml": '[project]\nname="reference"\nversion="0.1.0"\nrequires-python=">=3.13,<3.14"\ndependencies=[]\n',
            "system_packages": [],
            "stage_inputs_sh": "",
            "reference_script": "result = 1\nprint(result)\n",
            "artifacts": [
                {"path": "value.txt", "description": "value", "source_evidence": "result"}
            ],
            "excluded_outputs": [],
            "unresolved_assumptions": [],
            **changes,
        }
    )


def test_complete_script_is_preserved_and_diff_is_computed_without_execution():
    baseline = "result = 1\nresult = 1\n# Narrative stays here.\n"
    generated = baseline + "raise RuntimeError('must not execute')\n"
    script, diff = materialize(baseline, plan(reference_script=generated))
    assert script == generated
    assert "+raise RuntimeError" in diff
    assert "--- baseline.py" in diff and "+++ reference.py" in diff


@pytest.mark.parametrize("script", ["", "  \n", "result = (", "x = 1\nfrom __future__ import annotations\n"])
def test_missing_or_invalid_script_is_rejected_before_execution(script):
    with pytest.raises(ValueError, match="complete reference script|valid Python"):
        materialize("result = 1\n", plan(reference_script=script))


def test_patch_protocol_is_not_accepted_as_a_script():
    with pytest.raises(ValidationError, match="Extra inputs"):
        plan(changes=[])


def test_output_paths_and_inventory_fail_closed():
    with pytest.raises(ValidationError, match="relative"):
        plan(artifacts=[{"path": "../answer", "description": "x", "source_evidence": "x"}])
    with pytest.raises(ValidationError, match="unique endpoint artifacts"):
        plan(artifacts=[])
    with pytest.raises(ValidationError, match="unique endpoint artifacts"):
        plan(artifacts=[plan().artifacts[0].model_dump()] * 2)


@pytest.mark.parametrize("finding", ["Changed a threshold", "None detected; source unchanged"])
def test_approval_cannot_keep_a_known_scientific_change(finding):
    with pytest.raises(ValidationError, match="known blockers: prohibited_scientific_changes"):
        ReferenceReview(
            decision="approve",
            rationale="fixture",
            omitted_scientific_results=[],
            prohibited_scientific_changes=[finding],
            setup_or_export_problems=[],
            checks_for_execution=[],
        )


def test_upstream_revisions_share_the_request_ceiling_and_preserve_prompt(tmp_path):
    requests = []
    invalid = plan().model_dump()
    invalid["artifacts"] = []
    answers = [
        response("submit_artifact", invalid, 1),
        response("revise_artifact", {"patch": {"artifacts": plan().model_dump()["artifacts"]}}, 2),
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
    assert result.artifacts[0].path == "value.txt"
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


@pytest.mark.parametrize("always_truncated", [False, True])
def test_completed_token_limit_uses_only_one_upstream_recovery(tmp_path, always_truncated):
    from repo2rlenv.tasksmith.author.bridge import ProviderOutputError

    requests = []

    async def complete(payload):
        requests.append(payload)
        answer = response("submit_artifact", plan().model_dump(), len(requests))
        if always_truncated or len(requests) == 1:
            answer["choices"][0]["finish_reason"] = "length"
        return answer

    root = tmp_path / "stage"
    ledger = RequestLedger(tmp_path / "requests.sqlite", {"prepare-0": Allowance(3, 16000)})
    coroutine = stage(
        schema=ReferencePlan,
        name="prepare-0",
        prompt_name="notebook-reference-prepare",
        context={"baseline_script": "result = 1\n"},
        root=root,
        ledger=ledger,
        budget=AuthorBudget(
            RunBudget(BudgetLedger(tmp_path / "budget.sqlite", limit_usd="1"), "reference", "1"),
            tmp_path / "charges",
            "prepare-0",
        ),
        complete=complete,
        deadline=time.time() + 60,
        limits=ChatLimits(),
        max_requests=3,
    )
    if always_truncated:
        with pytest.raises(ProviderOutputError):
            asyncio.run(coroutine)
        assert not (root / "artifact-stage/draft.json").exists()
    else:
        assert asyncio.run(coroutine).artifacts[0].path == "value.txt"
    assert len(requests) == 2
    assert "Partial tool arguments were not executed" in requests[1]["messages"][1]["content"]
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 2
    operation = json.loads((root / "artifact-stage/operation.json").read_text())
    assert operation["provider_recovery"]["used_turns"] == 1


def test_durable_export_uses_provisioned_host_python(tmp_path, monkeypatch):
    import iris_bootstrap

    calls = []
    monkeypatch.setenv("BIOTASKS_EXPORT_PYTHON", "/provisioned/bin/python")
    monkeypatch.setattr(iris_bootstrap, "command", lambda *args, **kw: calls.append((args, kw)))
    root = tmp_path / "reference"
    deadline = time.time() + 60
    iris_bootstrap.export_on_host(root, "s3://fixture/reference", deadline=deadline)
    argv = calls[0][0][0]
    assert argv[0] == "/provisioned/bin/python"
    assert argv[2:] == ["--export", str(root), "s3://fixture/reference"]
    assert calls[0][1]["deadline"] == deadline
    assert not calls[0][1]["log"].is_relative_to(root)


def test_reference_payload_includes_bootstrap_diagnostic_dependency(tmp_path, monkeypatch):
    import hashlib

    import launch_reference

    archive = tmp_path / "upstream.tar.gz"
    archive.write_bytes(b"fixture archive")

    def frozen(repo, revision, path):
        if path.endswith("reference-execution.json"):
            return b'{"entrypoint":"run_reference.py"}'
        return path.encode()

    monkeypatch.setattr(launch_reference, "frozen_file", frozen)
    monkeypatch.setattr(
        launch_reference.subprocess, "check_output", lambda *a, **kw: b"git archive"
    )
    files = launch_reference.payload(tmp_path, revision="fixture", upstream_archive=archive)
    assert files["diagnostics.py"].endswith(b"/recover_evidence.py")
    manifest = json.loads(files["inputs.json"])
    assert (
        manifest["files"]["diagnostics.py"] == hashlib.sha256(files["diagnostics.py"]).hexdigest()
    )


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
    (source / "conversion.json").write_text(
        json.dumps(
            {
                "source_sha256": "fixture",
                "script_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
            }
        )
    )
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
                return CommandResult(
                    0,
                    json.dumps(
                        [
                            {"host": host, "port": port, "reachable": True}
                            for host, port in run_reference.TARGETS
                        ]
                    ),
                )
            if "stage-inputs" in argv:
                return CommandResult(0, '{"files": []}')
            return CommandResult(0, "")

    monkeypatch.setattr(
        run_reference, "Daytona", lambda: SimpleNamespace(create=lambda *a, **kw: Sandbox())
    )
    monkeypatch.setattr(run_reference, "DaytonaWorker", Worker)
    monkeypatch.setattr(
        iris_bootstrap, "export_on_host", lambda *a, **kw: events.append("durable-export")
    )

    def cleanup(*args):
        events.append("cleanup")
        return {"passed": True}

    monkeypatch.setattr(run_reference, "cleanup", cleanup)

    async def reviewed(**kwargs):
        if kwargs["schema"] is ReferencePlan:
            return plan()
        return ReferenceReview(
            decision="reject",
            rationale="Fixture scientific defect",
            omitted_scientific_results=[],
            prohibited_scientific_changes=["changed method"],
            setup_or_export_problems=[],
            checks_for_execution=[],
        )

    monkeypatch.setattr(run_reference, "stage", reviewed)
    result = asyncio.run(
        run_reference.run(
            config,
            seed={"source_sha256": "fixture"},
            root=tmp_path / "evidence",
            deadline=time.time() + 7200,
            endpoint="https://model.invalid/v1",
            credential="fake",
        )
    )
    assert result["status"] == "review_rejected" and result["cleanup_verified"]
    assert not any("execute" in argv for argv in commands)
    assert events == ["durable-export", "cleanup"]
