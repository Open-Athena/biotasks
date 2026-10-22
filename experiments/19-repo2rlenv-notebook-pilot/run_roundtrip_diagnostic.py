"""Private component experiment; never changes a task, grader, or original reward."""

import asyncio
import json
import os
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from design_stage import completion_transport
from iris_execution import IrisDaytonaExecution
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, inspect_bundle, write_bundle
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disposition: Literal["ready", "blocked"]
    code: str
    rationale: str


# The transport-success reward is explicitly NOT a task score. Preserve both
# original grader reports, including a failing stored branch, without regrading
# the original solver or changing any scientific acceptance criteria.
VERIFY = """import hashlib, json, subprocess
from pathlib import Path
root = Path('/workspace/outputs')
destination = Path('/logs/verifier')
destination.mkdir(parents=True, exist_ok=True)
expected = {c['id'] for c in json.loads(Path('/tests/checks.json').read_text())}
reports = {}
for branch in ('direct', 'stored'):
    path = destination / (branch + '.json')
    subprocess.run(['python', '/tests/grade.py', '--reference-dir', '/tests/reference',
                    '--submission-dir', str(root / branch), '--report', str(path)], check=True)
    report = json.loads(path.read_text())
    assert type(report['passed']) is bool
    assert len(report['checks']) == len(expected)
    assert {c['id'] for c in report['checks']} == expected
    assert all(type(c['passed']) is bool for c in report['checks'])
    assert report['passed'] == all(c['passed'] for c in report['checks'])
    reports[branch] = report
summary = {'diagnostic_only': True, 'original_solver_reward_changed': False,
           'baseline_matches_reference': reports['direct']['passed'],
           'stored_matches_reference': reports['stored']['passed'],
           'reports': reports}
(destination / 'report.json').write_text(json.dumps(summary, indent=2))
(destination / 'reward.txt').write_text('1\\n' if reports['direct']['passed'] else '0\\n')
"""


def diagnostic_bundle(original, destination, *, identity, code, revision, name):
    """Clone exact frozen assets; replace only experiment execution and reporting."""
    before = inspect_bundle(original)
    if not before["integrity_passed"] or before["bundle_hash"] != identity:
        raise ValueError("Diagnostic requires the exact original bundle")
    configuration = tomllib.loads((original / "task.toml").read_text())
    assets = {}
    for path in original.rglob("*"):
        if path.is_symlink():
            raise ValueError("Diagnostic bundle cannot contain symlinks")
        if path.is_file() and path.name != "task.toml" and path != original / "instruction.md":
            assets[path.relative_to(original).as_posix()] = TaskFile(
                path.read_bytes(), executable=bool(path.stat().st_mode & 0o111)
            )
    assets["solution/oracle.py"] = TaskFile.text(code)
    assets["tests/verify.py"] = TaskFile.text(VERIFY)
    result = write_bundle(
        TaskBundle(
            name=name,
            org="biotasks",
            instruction=(original / "instruction.md").read_text(),
            files=assets,
            metadata={
                "recipe": "saved-artifact-boundary-diagnostic",
                "recipe_version": revision,
                "reward_kinds": ["diagnostic-baseline-only"],
                "original_bundle_hash": identity,
                "not_a_benchmark_task_or_regrade": True,
            },
            environment=configuration["environment"],
            agent_timeout_sec=configuration["agent"]["timeout_sec"],
            verifier_timeout_sec=configuration["verifier"]["timeout_sec"],
        ),
        destination,
    )
    if inspect_bundle(original) != before:
        raise ValueError("Original task changed during diagnostic packaging")
    for relative in ("tests/grade.py", "tests/checks.json", "tests/outputs.json"):
        if (result / relative).read_bytes() != (original / relative).read_bytes():
            raise ValueError("Diagnostic altered the original grading contract")
    return result


async def run(config, *, root=Path("/evidence/roundtrip")):
    root.mkdir(parents=True, exist_ok=False)
    deadline = float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"])
    original = Path(os.environ["BIOTASKS_CONTINUATION"]) / "task"
    identity = inspect_bundle(original)
    if (
        not identity["integrity_passed"]
        or identity["bundle_hash"] != config["original_bundle_hash"]
    ):
        raise ValueError("Original task identity mismatch")
    context = {
        "instruction": (original / "instruction.md").read_text(),
        "reference_program": (original / "solution/oracle.py").read_text(),
        "output_paths": json.loads((original / "tests/outputs.json").read_text()),
        "environment": (original / "environment/pyproject.toml").read_text(),
    }
    ledger = RequestLedger(root / "requests.sqlite", {"diagnostic": Allowance(None, None)})
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "diagnostic", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort="high",
        request_timeout_sec=600,
    )

    async def validate(value):
        if not value.rationale.strip():
            raise ValueError("Diagnostic must explain its design or blocker")
        if value.disposition == "ready":
            if not value.code.strip():
                raise ValueError("Ready diagnostic needs a program")
            compile(value.code, "glm-roundtrip-diagnostic", "exec")
        elif value.code:
            raise ValueError("Blocked diagnostic must not contain executable code")

    async with AsyncOpenAI(
        base_url=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        api_key=os.environ["GLM_BULK_TOKEN"],
        max_retries=0,
        timeout=600,
        http_client=httpx.AsyncClient(follow_redirects=False),
    ) as client:
        experiment = await stage(
            schema=Experiment,
            name="diagnostic",
            prompt_name="notebook-roundtrip-diagnostic",
            context=context,
            root=root / "author",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "diagnostic"),
            complete=completion_transport(client),
            deadline=min(deadline, time.time() + 600),
            limits=limits,
            # One creation call, no semantic repair or tool-use session.
            max_requests=1,
            validate=validate,
            recover_output_limit=False,
            output_format="json_schema",
        )
    save_record(root / "experiment.json", experiment.model_dump())
    result = dict(
        status="blocked" if experiment.disposition == "blocked" else "incomplete",
        original_bundle_hash=identity["bundle_hash"],
        original_artifacts_changed=False,
        original_solver_reward_changed=False,
        new_full_pipeline_run=False,
        publication_ready=False,
        requested_reasoning_effort="high",
        effective_served_effort_verified=False,
        rationale=experiment.rationale,
    )
    if experiment.disposition == "ready":
        revision = json.loads(Path("/evidence/inputs.json").read_text())["factory_revision"]
        task = diagnostic_bundle(
            original,
            root / "tasks",
            identity=identity["bundle_hash"],
            code=experiment.code,
            revision=revision,
            name=config["campaign"],
        )
        save_record(root / "identity.json", inspect_bundle(task))
        usage = BudgetLedger(root / "daytona-budget.sqlite", limit_usd="1")
        usage.reserve("storage", "0.10", "Diagnostic image storage margin")
        adapter = IrisDaytonaExecution(
            worker_id=os.environ["BIOTASKS_IRIS_WORKER_ID"],
            deadline=datetime.fromtimestamp(deadline, UTC),
            records=root / "trial-claims",
            max_trials=1,
            max_solver_attempts=1,
            usage_ledger=usage,
            task_resources={"cpus": 4, "memory_mb": 8192, "storage_mb": 10240},
            solver_seconds=600,
            trial_reservation_usd="0.25",
        )
        save_record(root / "execution.json", adapter.identity())
        trial = adapter.run_trial(
            adapter.worker,
            task,
            root / "native",
            trial_id=config["campaign"],
            agent="oracle",
            python=sys.executable,
            ledger=BudgetLedger(root / "trial-model-budget.sqlite", limit_usd="1"),
            reservation_usd="1",
            max_turns=None,
            max_tokens=None,
            timeout_sec=1500,
        )
        result.update(
            status="diagnostic_executed" if trial.completed else "infrastructure_failure",
            diagnostic_baseline_reward=trial.reward,
            exception_type=trial.exception_type,
            result_path=str(trial.result.relative_to(root)),
            cleanup_verified=True,
            original_bundle_still_matches=inspect_bundle(original) == identity,
        )
    save_record(root / "result.json", result)
    return result


if __name__ == "__main__":
    config = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    if config["entrypoint"] != "run_roundtrip_diagnostic.py":
        raise ValueError("Wrong component entrypoint")
    asyncio.run(run(config))
