"""Observed artifacts -> GLM endpoint proposal -> separate coverage review."""

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from coverage_protocol import CoveragePlan, CoverageReview, validate_evidence
from design_stage import completion_transport
from inspect_artifacts import digest, relative_path
from openai import AsyncOpenAI
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


def check_config(config, prior, previous=()):
    consumed = sum(item["model_request_slots_used"] for item in previous)
    if (
        config["entrypoint"] != "run_coverage.py"
        or not 1 <= config["coverage_requests"] <= 6
        or not 1 <= config["review_requests"] <= 3
        or config["max_requests"] != config["coverage_requests"] + config["review_requests"]
        or consumed < 0
        or config["max_requests"] + consumed > 9
        or config["max_requests"] + consumed + prior["raw_model_requests"]
        > config["pipeline_request_ceiling"]
        or config["pipeline_request_ceiling"] > 80
    ):
        raise ValueError("Coverage stage exceeds its recorded request allowance")


async def run(config, *, root, seed, endpoint, credential, deadline):
    experiment = Path(__file__).parent
    prior = experiment / relative_path(config["reference_run"])
    summary = json.loads((prior / "summary.json").read_text())
    previous_paths = config.get("previous_coverage_results", [])
    if len(set(previous_paths)) != len(previous_paths):
        raise ValueError("Duplicate prior coverage result")
    previous = [
        json.loads((experiment / relative_path(path)).read_text()) for path in previous_paths
    ]
    check_config(config, summary, previous)
    prior_requests = summary["raw_model_requests"] + sum(
        item["model_request_slots_used"] for item in previous
    )
    source = experiment / relative_path(config["source_directory"])
    conversion = json.loads((source / "conversion.json").read_text())
    recorded_conversion = json.loads((prior / "conversion.json").read_text())
    if recorded_conversion["script_sha256"] != conversion["script_sha256"]:
        raise ValueError(
            "Saved reference uses a different script; execute the current reference first"
        )
    if (
        digest(source / "baseline.py") != conversion["script_sha256"]
        or seed["source_sha256"] != conversion["source_sha256"]
    ):
        raise ValueError("Source identity mismatch")
    attempt = prior / ("attempt-" + str(summary["successful_attempt"]))
    observations = json.loads((root / "profiles/all.json").read_text())
    original = json.loads((attempt / "artifacts.json").read_text())["artifacts"]
    if [(x["path"], x["sha256"]) for x in observations] != [
        (x["path"], x["sha256"]) for x in original
    ]:
        raise ValueError("Profiles do not match the pinned reference inventory")
    save_record(root / "configuration.json", config)
    context = dict(
        source={key: value for key, value in seed.items() if key != "question_text"},
        baseline_script=(source / "baseline.py").read_text(),
        executed_script=(attempt / "reference.py").read_text(),
        source_diff=(attempt / "source.diff").read_text(),
        prior_plan=json.loads((attempt / "plan.json").read_text()),
        prior_review=json.loads((attempt / "review.json").read_text()),
        execution=json.loads((attempt / "execution.json").read_text()),
        reference_summary=summary,
        observations=observations,
        boundary="Coverage proposal only; no grading or independent scientific validation yet.",
    )
    ledger = RequestLedger(
        root / "requests.sqlite",
        {
            name: Allowance(config[name + "_requests"], config["max_output_tokens"])
            for name in ("coverage", "review")
        },
    )
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "coverage", "1")
    limits = ChatLimits(
        max_output_tokens=config["max_output_tokens"],
        max_input_bytes=config["max_input_bytes"],
        request_timeout_sec=config["request_timeout_seconds"],
        reasoning_effort=config["reasoning_effort"],
    )
    result = dict(
        status="started",
        started=time.time(),
        reference_rerun=False,
        construction_run=False,
        solver_run=False,
        semantic_fidelity_validated=False,
        daytona_sandboxes_created=0,
        prior_pipeline_requests=prior_requests,
    )
    client = AsyncOpenAI(
        base_url=endpoint,
        api_key=credential,
        max_retries=0,
        timeout=limits.request_timeout_sec,
        http_client=httpx.AsyncClient(follow_redirects=False),
    )

    async def call(schema, name, prompt, inputs, validator=None):
        return await stage(
            schema=schema,
            name=name,
            prompt_name=prompt,
            context=inputs,
            root=root / name,
            ledger=ledger,
            budget=AuthorBudget(budget, root / name / "charges", name),
            complete=completion_transport(client),
            deadline=deadline,
            limits=limits,
            max_requests=config[name + "_requests"],
            validate=validator,
        )

    async def validate(plan):
        validate_evidence(plan, observations)

    try:
        plan = await call(CoveragePlan, "coverage", "notebook-endpoint-coverage", context, validate)
        save_record(root / "endpoint-proposal.json", plan.model_dump())
        review = await call(
            CoverageReview,
            "review",
            "notebook-endpoint-review",
            {**context, "endpoint_proposal": plan.model_dump()},
        )
        save_record(root / "coverage-review.json", review.model_dump())
        result.update(
            status="coverage_proposed"
            if plan.disposition == "propose_contract" and review.decision == "approve"
            else "further_reference_or_coverage_work_required",
            disposition=plan.disposition,
            review_decision=review.decision,
        )
    except BaseException as error:
        result.update(status="incomplete", error_type=type(error).__name__)
        raise
    finally:
        await client.close()
        with sqlite3.connect(ledger.path) as db:
            states = dict(db.execute("SELECT state, COUNT(*) FROM calls GROUP BY state").fetchall())
        result["request_states"] = states
        result["model_request_slots_used"] = sum(states.values())
        result["pipeline_request_slots_used"] = prior_requests + sum(states.values())
        result["finished"] = time.time()
        save_record(root / "result.json", result)


if __name__ == "__main__":
    asyncio.run(
        run(
            json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text()),
            root=Path("/evidence/coverage"),
            seed=json.loads(Path(os.environ["BIOTASKS_SEED"]).read_text())[0],
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
        )
    )
