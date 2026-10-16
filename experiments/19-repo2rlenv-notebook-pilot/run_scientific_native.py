"""Execute frozen validated tasks with upstream Harbor trials; never author tasks."""

import json
import os
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path

from iris_bootstrap import export_on_host
from iris_execution import IrisDaytonaExecution
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.spec.input import LLMSpec
from scientific_bundle import package

from biotasks.inference_gate import Allowance, InferenceGate, RequestLedger

HERE = Path(__file__).parent


def archive_task(task, root, deadline):
    """Preserve the exact pre-trial bundle for inspection and eventual release."""
    directory = root / "package"
    directory.mkdir()
    identity = inspect_bundle(task)
    if not identity["integrity_passed"]:
        raise ValueError("Native task bundle identity failed")
    with tarfile.open(directory / "task.tar.gz", "w:gz") as archive:
        archive.add(task, arcname=task.name)
    if inspect_bundle(task) != identity:
        raise ValueError("Native task changed during archival")
    save_record(directory / "identity.json", identity)
    export_on_host(
        directory,
        os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/") + "/native/package",
        deadline=deadline,
    )


def run(config, *, root=Path("/evidence/native")):
    if (root / "started.json").exists():
        raise FileExistsError("Reconcile the existing native campaign")
    deadline = float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"])
    save_record(root / "started.json", dict(config=config, started=time.time()))
    task = package(
        materialization=root / "materialized",
        grading=HERE / config["grading_directory"],
        environment=HERE / config["reference_directory"],
        destination=root / "tasks",
        name=config["task_name"],
        revision=config["factory_revision"],
        attribution=json.loads((HERE / config["attribution_file"]).read_text()),
    )
    archive_task(task, root, deadline)
    requests = RequestLedger(root / "requests.sqlite", {"solver": Allowance(None, None)})
    gate = InferenceGate(
        upstream=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        credential=os.environ["GLM_BULK_TOKEN"],
        model="glm-5.3",
        ledger=requests,
        deadline=deadline,
        request_timeout=600,
        chat_template_kwargs={"reasoning_effort": "medium"},
    ).start()
    result = dict(status="incomplete", controls=[], solver=None, publication_ready=False)
    try:
        usage = BudgetLedger(root / "daytona-budget.sqlite", limit_usd=config["daytona_budget_usd"])
        usage.reserve("storage", "0.10", "Conservative native image storage allowance")
        adapter = IrisDaytonaExecution(
            worker_id=os.environ["BIOTASKS_IRIS_WORKER_ID"],
            deadline=datetime.fromtimestamp(deadline, UTC),
            records=root / "trial-claims",
            max_trials=3,
            max_solver_attempts=1,
            solver_endpoints=(gate.endpoint("solver"), gate.endpoint("solver")),
            usage_ledger=usage,
            task_resources={"cpus": 4, "memory_mb": 8192, "storage_mb": 10240},
            solver_seconds=600,
            trial_reservation_usd="0.25",
        )
        save_record(root / "execution.json", adapter.identity())
        model_budget = BudgetLedger(root / "model-budget.sqlite", limit_usd="1")
        for agent, expected in [("oracle", 1), ("nop", 0), ("terminus-2", None)]:
            kwargs = {}
            if agent == "terminus-2":
                kwargs["model"] = LLMSpec(
                    provider="openai",
                    model="glm-5.3",
                    endpoint=gate.endpoint("solver"),
                    api_key_env="GLM_BULK_TOKEN",
                    timeout_sec=600,
                    max_concurrent=1,
                    model_info={
                        "max_input_tokens": 120000,
                        "input_cost_per_token": 0,
                        "output_cost_per_token": 0,
                    },
                )
            trial = adapter.run_trial(
                adapter.worker,
                task,
                root / agent,
                trial_id=config["campaign"] + "-" + agent,
                agent=agent,
                ledger=model_budget,
                reservation_usd="1",
                max_turns=None,
                max_tokens=None,
                timeout_sec=1500,
                **kwargs,
            )
            record = dict(
                agent=agent,
                reward=trial.reward,
                exception_type=trial.exception_type,
                result_path=str(trial.result.relative_to(root)),
                cleanup_verified=True,
            )
            if expected is None:
                result["solver"] = record
            else:
                record["expected_reward"] = expected
                record["passed"] = trial.completed and trial.reward == expected
                result["controls"].append(record)
                if not record["passed"]:
                    raise ValueError("Native " + agent + " control failed")
            save_record(root / "result.json", result)
        result["status"] = "native_validated_solver_attempt_recorded"
        # Solver success is not an acceptance condition. Infrastructure failure
        # remains separately visible and requires review before release.
        result["publication_ready"] = result["solver"]["reward"] in {0, 1} and result["solver"][
            "exception_type"
        ] in {None, "AgentTimeoutError"}
    finally:
        gate.close()
        result["finished"] = time.time()
        save_record(root / "result.json", result)
    return result


if __name__ == "__main__":
    config = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    if config["entrypoint"] != "run_scientific_native.py":
        raise ValueError("Wrong native entrypoint")
    config["factory_revision"] = json.loads(Path("/evidence/inputs.json").read_text())[
        "factory_revision"
    ]
    run(config)
