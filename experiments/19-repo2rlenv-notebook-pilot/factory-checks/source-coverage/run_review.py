"""Re-review an unchanged recorded context with the canonical GLM reviewer.

This diagnostic uses no shell or sandbox and never edits scientific artifacts.
It is separate from the original campaign and is not a fresh pipeline run.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from grading_protocol import Review, check_review_source_coverage
from openai import AsyncOpenAI
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


async def run(input_file, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    raw = Path(input_file).read_bytes()
    context = json.loads(raw)
    deadline = min(time.time() + 600, float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]))
    ledger = RequestLedger(root / "requests.sqlite", {"review": Allowance(None, None)})
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "review", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort="high",
        request_timeout_sec=600,
    )

    async def validate(value):
        check_review_source_coverage(value)
        if value.decision == "accept_for_packaging" and (
            value.issues or not all(c["passed_control"] for c in context["controls"])
        ):
            raise ValueError("Acceptance requires passing controls and no unresolved issues")

    async with AsyncOpenAI(
        base_url=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        api_key=os.environ["GLM_BULK_TOKEN"],
        max_retries=0,
        timeout=600,
        http_client=httpx.AsyncClient(follow_redirects=False),
    ) as client:
        review = await stage(
            schema=Review,
            name="review",
            prompt_name="notebook-grader-review",
            context=context,
            root=root / "review",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "review"),
            complete=completion_transport(client),
            deadline=deadline,
            limits=limits,
            max_requests=None,
            validate=validate,
            recover_output_limit=False,
        )
    save_record(root / "review.json", review.model_dump())
    save_record(
        root / "result.json",
        {
            "status": "review_completed",
            "recorded_context_sha256": hashlib.sha256(raw).hexdigest(),
            "model": "glm-5.3",
            "reasoning_effort_requested": "high",
            "served_endpoint_effective_effort_verified": False,
            "scientific_execution": False,
            "new_daytona_sandboxes": 0,
            "original_artifacts_changed": False,
            "new_pipeline_run": False,
            "decision": review.decision,
        },
    )
    return review
