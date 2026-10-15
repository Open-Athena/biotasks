"""Review executed evidence and draft a task in one call; no construction."""

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from openai import AsyncOpenAI
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget
from specification_inputs import specification_context
from specification_protocol import TaskSpecification

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


async def run(config, *, root, endpoint, credential, deadline, complete=None):
    if config["entrypoint"] != "run_specification.py" or config["max_requests"] != 1:
        raise ValueError("Specification requires exactly one call with no automatic repair")
    root.mkdir(parents=True, exist_ok=False)
    experiment = Path(__file__).parent
    context = specification_context(
        experiment / config["reference_directory"],
        json.loads((experiment / config["policy_file"]).read_text()),
    )
    expected = json.loads((experiment / config["input_file"]).read_text())
    if context != expected:
        raise ValueError("Specification context differs from the reviewed input bundle")
    save_record(root / "configuration.json", config)
    ledger = RequestLedger(root / "requests.sqlite", {"specify": Allowance(1, None)})
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "specify", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort="medium",
        request_timeout_sec=config["request_timeout_seconds"],
    )
    result = dict(
        status="started",
        started=time.time(),
        setup_executed=False,
        scientific_analysis_executed=False,
        endpoint_review_requested=True,
        construction_run=False,
        solver_run=False,
        daytona_sandboxes_created=0,
        model="glm-5.3",
        reasoning_effort="medium",
        output_token_policy="No client max_tokens; provider limits/defaults apply.",
        provider_generation_limit_verified=False,
    )
    client = None

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
            schema=TaskSpecification,
            name="specify",
            prompt_name="notebook-task-specification",
            context=context,
            root=root / "specify",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "specify"),
            complete=complete,
            deadline=deadline,
            limits=limits,
            max_requests=1,
            recover_output_limit=False,
            output_format="json_schema",
        )
        save_record(root / "specification.json", plan.model_dump())
        (root / "review.md").write_text(plan.review + "\n")
        (root / "validation-plan.md").write_text(plan.validation_plan + "\n")
        if plan.task_brief:
            (root / "task-brief.md").write_text(plan.task_brief + "\n")
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
            root=Path("/evidence/specification"),
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
        )
    )
