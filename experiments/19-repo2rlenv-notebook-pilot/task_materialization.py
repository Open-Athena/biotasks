"""Tasksmith session for explicit supplied inputs and a separately executed oracle."""

import json
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from materialization_protocol import Materialization
from openai import AsyncOpenAI
from reference_replay import sha256
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger

HERE = Path(__file__).parent


async def run_materialization(
    *, session, context, root, config, endpoint, credential, deadline, complete=None
):
    source = session.snapshot["directory"]
    context = {
        **context,
        "original_inputs": json.loads((source / "trial/inputs-before.json").read_text()),
        "reference_seconds": config["reference_seconds"],
    }
    ledger = RequestLedger(root / "requests.sqlite", {"materialize": Allowance(None, None)})
    budget = RunBudget(
        BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "materialize", "1"
    )
    client = None
    if complete is None:
        client = AsyncOpenAI(
            base_url=endpoint,
            api_key=credential,
            max_retries=0,
            timeout=config["request_timeout_seconds"],
            http_client=httpx.AsyncClient(follow_redirects=False),
        )
        complete = completion_transport(client)
    attempts = []

    async def validate(candidate):
        if candidate.disposition == "blocked":
            return
        folder = root / "materialization" / str(len(attempts) + 1)
        folder.mkdir(parents=True)
        record = candidate.model_dump()
        record["seconds"] = config["reference_seconds"]
        save_record(folder / "candidate.json", record)
        await session.remote.upload(
            folder / "candidate.json", "/work/grading-private/materialization.json"
        )
        for name in ("materialization_remote.py", "grading_remote.py"):
            await session.remote.upload(HERE / name, "/work/" + name)
        started = time.time()
        reply = await session.command(
            ["python", "/work/materialization_remote.py"],
            2 * config["reference_seconds"] + 60,
            "materialize-" + str(len(attempts) + 1),
        )
        result = {"controller": reply, "elapsed_seconds": time.time() - started}
        attempts.append(result)
        if reply["exit_code"] == 0:
            result["execution"] = json.loads(reply["log"])
        save_record(folder / "result.json", result)
        if (
            reply["exit_code"]
            or result["execution"]["status"] != "executed_requires_scientific_validation"
        ):
            raise ValueError("Materialization/oracle execution failed: " + json.dumps(result))

    try:
        candidate = await stage(
            schema=Materialization,
            name="materialize",
            prompt_name="notebook-task-materialize",
            context=context,
            root=root / "materialize",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "materialize"),
            complete=complete,
            deadline=deadline,
            limits=ChatLimits(
                max_output_tokens=None,
                max_input_bytes=None,
                max_response_bytes=None,
                tool_output_chars=None,
                reasoning_effort="medium",
                request_timeout_sec=config["request_timeout_seconds"],
            ),
            max_requests=None,
            validate=validate,
            shell=session.shell,
            recover_output_limit=False,
        )
        save_record(root / "materialization-candidate.json", candidate.model_dump())
        if candidate.disposition == "blocked":
            return {"status": "materialization_blocked"}
        execution = attempts[-1]["execution"]
        saved = root / "materialized"
        for kind, remote_root in (
            ("inputs", "/work/grading-private/materialized/inputs"),
            ("reference", "/work/grading-private/materialized/reference"),
            ("oracle_outputs", "/task/outputs"),
        ):
            for item in execution[kind]:
                path = saved / kind / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                await session.remote.download(remote_root + "/" + item["path"], path)
                if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                    raise ValueError("Downloaded derived artifact identity mismatch")
        for name, content in [
            ("instruction.md", candidate.instruction),
            ("derive.py", candidate.derive_code),
            ("oracle.py", candidate.oracle_code),
            ("rationale.md", candidate.rationale),
        ]:
            (saved / name).write_text(content + "\n")
        save_record(saved / "manifest.json", execution)
        return {
            "status": "materialized_requires_scientific_validation",
            "materialization_attempts": len(attempts),
            "oracle_executed": True,
            "oracle_answers_isolated": True,
            "numerical_comparison_validated": False,
        }
    finally:
        if client:
            await client.close()
