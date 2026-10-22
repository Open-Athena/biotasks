"""Run preparation with at most one validation-driven repair, then inspection.

No data staging, sandbox, shell tool, model review or scientific execution.
Generated commands remain inert files for the user's inspection.
"""

import asyncio
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from model_profile import native_effort
from openai import AsyncOpenAI
from reference_protocol import ReferencePlan, materialize
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


def preparation_context(source, seed, target):
    baseline = (source / "baseline.py").read_text()
    conversion = json.loads((source / "conversion.json").read_text())
    if (
        hashlib.sha256(baseline.encode()).hexdigest() != conversion["script_sha256"]
        or seed["source_sha256"] != conversion["source_sha256"]
    ):
        raise ValueError("Source identity mismatch")
    return {
        "source": {key: value for key, value in seed.items() if key != "question_text"},
        "baseline_script": baseline,
        "conversion": conversion,
        "limits": target,
    }


async def run(config, *, root, seed, endpoint, credential, deadline, complete=None):
    config = {**config, "reasoning_effort": native_effort(config)}
    if (
        config["entrypoint"] != "run_preparation.py"
        or type(config["max_requests"]) is not int
        or config["max_requests"] not in {1, 2}
    ):
        raise ValueError("Preparation allows one creation call and at most one validation repair")
    root.mkdir(parents=True, exist_ok=False)
    experiment = Path(__file__).parent
    context = preparation_context(experiment / config["source_directory"], seed, config["target"])
    save_record(root / "configuration.json", config)
    ledger = RequestLedger(
        root / "requests.sqlite", {"prepare": Allowance(config["max_requests"], None)}
    )
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "prepare", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort=native_effort(config),
        request_timeout_sec=config["request_timeout_seconds"],
    )
    result = dict(
        status="started",
        started=time.time(),
        setup_executed=False,
        scientific_analysis_executed=False,
        independent_review_run=False,
        daytona_sandboxes_created=0,
        model="glm-5.3",
        reasoning_effort=native_effort(config),
        output_token_policy="No client max_tokens; provider limits/defaults apply.",
        provider_generation_limit_verified=False,
    )
    client = None

    async def validate(plan):
        if plan.disposition == "prepare":
            materialize(context["baseline_script"], plan)

    try:
        if complete is None:
            client = AsyncOpenAI(
                base_url=endpoint,
                api_key=credential,
                max_retries=0,
                timeout=limits.request_timeout_sec,
                http_client=httpx.AsyncClient(follow_redirects=False),
            )
            complete = completion_transport(client)
        plan = await stage(
            schema=ReferencePlan,
            name="prepare",
            prompt_name="notebook-reference-prepare",
            context=context,
            root=root / "prepare",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "prepare"),
            complete=complete,
            deadline=deadline,
            limits=limits,
            max_requests=config["max_requests"],
            validate=validate,
            recover_output_limit=False,
            output_format="json_schema",
            response_recovery=False,
        )
        save_record(root / "plan.json", plan.model_dump())
        if plan.disposition == "prepare":
            script, diff = materialize(context["baseline_script"], plan)
            (root / "exports.py").write_text(plan.export_code)
            (root / "reference.py").write_text(script)
            (root / "source.diff").write_text(diff)
        result.update(status="ready_for_user_inspection", disposition=plan.disposition)
    except BaseException as error:
        result.update(status="incomplete", error_type=type(error).__name__)
        raise
    finally:
        if client is not None:
            await client.close()
        with sqlite3.connect(ledger.path) as db:
            states = dict(db.execute("SELECT state, COUNT(*) FROM calls GROUP BY state").fetchall())
        result.update(
            request_states=states,
            model_request_slots_used=sum(states.values()),
            finished=time.time(),
        )
        save_record(root / "result.json", result)


if __name__ == "__main__":
    asyncio.run(
        run(
            json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text()),
            root=Path("/evidence/preparation"),
            seed=json.loads(Path(os.environ["BIOTASKS_SEED"]).read_text())[0],
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
        )
    )
