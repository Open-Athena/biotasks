"""One bounded upstream campaign, executed only inside its allocated Iris job."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from functools import partial
from importlib.resources import files
from pathlib import Path

from daytona import Daytona
from fidelity import review as review_fidelity
from iris_execution import IrisDaytonaExecution
from preflight import run as run_preflight
from pydantic import BaseModel, ConfigDict
from quality_guidance import GuidedModel
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.llm import complete
from repo2rlenv.pipelines.recipes.seta_seed2synth import recipe
from repo2rlenv.pipelines.recipes.terminal.runner import run_synthesis
from repo2rlenv.quality.loop.models import LoopOptions
from repo2rlenv.quality.loop.runner import QualityLoop
from repo2rlenv.spec.input import GenerationInput, LLMSpec
from repo2rlenv.spec.recipe_options import TerminalSynthesisOptions

from biotasks.inference_gate import Allowance, InferenceGate, RequestLedger


class Compatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")
    compatible: bool


class EscapedText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: str


def emit(event):
    print("BIOTASKS19_EVENT " + event.model_dump_json(), flush=True)


def run(
    *,
    root: Path,
    endpoint: str,
    worker_id: str,
    deadline: float,
    wheel: Path,
    notebook_seed: Path,
    config: dict,
    continuation: Path | None = None,
):
    imported = {}
    continuation_task = None
    if continuation is not None:
        from quality_continuation import load, remaining_config

        continuation_task, imported, plan = load(continuation)
        config = remaining_config(config, plan)
    root.mkdir(parents=True, exist_ok=True)
    if (root / "started.json").exists():
        raise FileExistsError(
            "Existing campaign must be reconciled, never automatically relaunched"
        )
    save_record(
        root / "started.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "config": config,
            "seed_sha256": hashlib.sha256(notebook_seed.read_bytes()).hexdigest(),
        },
    )
    requests = RequestLedger(
        root / "requests.sqlite",
        {k: Allowance(**v) for k, v in config["request_allowances"].items()},
    )
    gate = InferenceGate(
        upstream=endpoint,
        credential=os.environ["GLM_BULK_TOKEN"],
        model=config["model"],
        ledger=requests,
        deadline=deadline,
        chat_template_kwargs=config.get("chat_template_kwargs"),
        structured_output_mode=config.get("structured_output_mode", "json_schema"),
    ).start()
    try:

        def model(scope):
            return LLMSpec(
                provider="openai",
                model=config["model"],
                endpoint=gate.endpoint(scope),
                api_key_env="GLM_BULK_TOKEN",
                timeout_sec=180,
                max_concurrent=1,
                model_info={
                    "max_input_tokens": 120000,
                    "max_output_tokens": 8192,
                    "input_cost_per_token": 0,
                    "output_cost_per_token": 0,
                },
            )

        if config["request_allowances"]["compatibility"]["requests"]:
            reply = complete(
                model("compatibility"),
                system="Return only the requested JSON object.",
                user='Return {"compatible": true}.',
                max_tokens=512,
                temperature=0,
                response_schema=Compatibility.model_json_schema(),
            )
            checked = Compatibility.model_validate_json(reply.content)
            save_record(
                root / "compatibility.json",
                {"passed": checked.compatible, "usage": reply.usage, "content": reply.content},
            )
            if not checked.compatible:
                raise RuntimeError("Structured completion preflight failed")
            expected = 'first line\n    second line\t"quoted"\\path\nλ'
            escaped = complete(
                model("compatibility"),
                system="Return only the requested JSON object, preserving every string character.",
                user="Return this exact object: " + json.dumps({"payload": expected}),
                max_tokens=512,
                temperature=0,
                response_schema=EscapedText.model_json_schema(),
            )
            save_record(
                root / "escaping-compatibility.json",
                {"expected": expected, "content": escaped.content, "usage": escaped.usage},
            )
            if EscapedText.model_validate_json(escaped.content).payload != expected:
                raise RuntimeError(
                    "Structured completion altered code-significant string characters"
                )
        daytona_usage = BudgetLedger(
            root / "daytona-budget.sqlite3", limit_usd=config["daytona_budget_usd"]
        )
        daytona_usage.reserve("storage", "0.058", "Campaign image/storage allowance")
        daytona_usage.reserve("preflight", "0.030", "Single infrastructure preflight")
        preflight = run_preflight(
            Daytona(), root=root, campaign=config["campaign"], deadline=deadline
        )
        if not preflight.get("passed") or not preflight.get("cleanup_verified"):
            raise RuntimeError("Infrastructure preflight is incomplete")
        campaign = root / "campaign"
        campaign.mkdir()
        # Upstream monetary reservations are preserved as bookkeeping, separate
        # from the enforced raw-request quota and actual Daytona cost ceiling.
        ledger = BudgetLedger(campaign / "budget.sqlite3", limit_usd="50")
        execution = IrisDaytonaExecution(
            worker_id=worker_id,
            deadline=datetime.fromtimestamp(deadline, UTC),
            records=root / "trial-claims",
            max_trials=config["max_trials"],
            max_solver_attempts=config["max_solver_attempts"],
            solver_endpoints=(
                gate.endpoint("solver-2" if continuation else "solver-1"),
                gate.endpoint("solver-2"),
            ),
            usage_ledger=daytona_usage,
        )
        seed = json.loads(notebook_seed.read_text())[0]
        guidance = files("biotasks.prompts").joinpath("notebook-grounding.md").read_text()
        guidance += "\n\nController-selected scope and input provenance:\n" + json.dumps(
            seed["input_manifest"]
        )
        guidance += "\n\nTask budget: 1 CPU, 2 GiB RAM, 10 GiB disk, no GPU; solver 300 seconds."
        save_record(root / "authoring-guidance.json", {"system_guidance": guidance})
        if continuation_task is None:
            input_spec = GenerationInput.model_validate(
                {
                    "source": {"kind": "seeds", "path": str(notebook_seed)},
                    "pipeline": {"name": "terminal_synth", "recipe": "seta_seed2synth"},
                    "llm": model("generation").model_dump(),
                    "output": {
                        "destination": str(root / "tasks"),
                        "org": "biotasks",
                        "dataset_name": "notebook-pilot-issue-19",
                    },
                    "execution": {
                        "worker_receipt": str(root / "worker.json"),
                        "runtime_wheel": str(wheel),
                        "campaign_dir": str(campaign),
                        "run_id": config["campaign"],
                        "timeout_sec": max(60, int(deadline - time.time())),
                    },
                }
            )
            save_record(root / "generation-input.json", input_spec.model_dump(mode="json"))
            result = run_synthesis(
                input_spec,
                TerminalSynthesisOptions(
                    target=1,
                    max_candidates=1,
                    max_repairs=config["max_generation_repairs"],
                    max_tokens=16000,
                    # Upstream adds 30 seconds of grader overhead to this test limit.
                    test_timeout_sec=90,
                ),
                root / "tasks",
                emit,
                designer=partial(recipe.design, system_guidance=guidance),
                builder_prompt=recipe.builder_prompt() + "\n\n" + guidance,
                execution_adapter=execution,
            )
            save_record(
                root / "generation-summary.json",
                {
                    "emitted": result.emitted,
                    "skipped": result.skipped,
                    "skip_reasons": result.skip_reasons,
                },
            )
            if result.emitted != 1:
                return {"status": "generation_failed", "completion_requirements_met": False}
            tasks = list((root / "tasks").glob("*/task.toml"))
            if len(tasks) != 1:
                raise RuntimeError("Expected exactly one emitted task")
            selected_task = tasks[0].parent
        else:
            selected_task = continuation_task
        options = LoopOptions(
            review_model=model("quality"),
            repair_model=model("quality"),
            solver_model=model("solver-1"),
            repair=True,
            run_rollout=True,
            max_repairs=config["max_quality_repairs"],
            max_read_rounds=2,
            max_probes=2,
            max_turns=config["solver_turns"],
            solver_tokens=8192,
            model_tokens=8000,
            trial_timeout_sec=config["trial_seconds"],
            max_spend_usd="40",
        )
        loop = QualityLoop(
            options,
            root / "quality",
            ledger,
            on_event=emit,
            task_context={
                "campaign_design_guidance": guidance,
                "notebook_source": seed["question_text"],
            },
        )
        loop.model = GuidedModel(
            loop.model, files("biotasks.prompts").joinpath("notebook-quality.md").read_text()
        )
        loop.remote = execution.quality_trials(
            directory=root / "quality", budget=loop.budget, options=options
        )
        if continuation is not None:
            from quality_continuation import restore_probe_cache

            restore_probe_cache(continuation, root / "quality", plan)
        quality = loop.run(selected_task, **imported)
        save_record(root / "quality-result.json", quality.model_dump(mode="json"))
        fidelity = review_fidelity(
            task=Path(quality.task_path),
            seed=seed,
            quality=quality.model_dump(mode="json"),
            model=model("quality"),
            directory=root / "fidelity",
        )
        return {
            "status": quality.status,
            "completion_requirements_met": False,
            "scientific_review_supported": fidelity["supported"],
            "remaining": ["execution_evidence_audit", "release_and_download_check"],
        }
    finally:
        gate.close()


if __name__ == "__main__":
    configuration = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    outcome = run(
        root=Path("/evidence/pilot"),
        endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        worker_id=os.environ["BIOTASKS_IRIS_WORKER_ID"],
        deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
        wheel=Path(os.environ["BIOTASKS_RUNTIME_WHEEL"]),
        notebook_seed=Path(os.environ["BIOTASKS_SEED"]),
        config=configuration,
        continuation=Path(os.environ["BIOTASKS_CONTINUATION"])
        if os.environ.get("BIOTASKS_CONTINUATION")
        else None,
    )
    save_record(Path("/evidence/pilot/outcome.json"), outcome)
    print(json.dumps(outcome), flush=True)
