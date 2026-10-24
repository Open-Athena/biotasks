"""Reference preparation/review using the pinned Tasksmith artifact controller."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.tasksmith.author.artifact import artifact_stage, canonical_digest
from repo2rlenv.tasksmith.author.bridge import ProviderOutputError

from biotasks.chat_author import GLMChatAuthor, OutputTokenLimit


async def stage(
    *,
    schema,
    name,
    prompt_name,
    context,
    root,
    ledger,
    budget,
    complete,
    deadline,
    limits,
    max_requests,
    validate=None,
    recover_output_limit=True,
    output_format="tools",
    shell=None,
    shell_timeout_sec=120,
    extra_tools=None,
    extra_handlers=None,
    response_recovery=True,
):
    """Use recorded empty-response recovery and upstream's output recovery.

    Recovery consumes the existing request/turn allowance and deadline. A
    one-call stage has no spare turn for recovery. At most one retry after a
    timeout or typed model-connection failure may repeat pure generation without
    replaying tool actions; its original slot remains uncertain. This allowance
    is shared across those two failure types. Other failures remain terminal.
    """
    prompt = files("biotasks.prompts").joinpath(prompt_name + ".md").read_text()
    recovery_notice = (
        files("biotasks.prompts").joinpath("worker-context-recovery.md").read_text()
        if shell is not None or extra_tools
        else None
    )
    runtime_budget_notice = (
        files("biotasks.prompts").joinpath("worker-runtime-budget.md").read_text()
        if shell is not None or extra_tools
        else None
    )
    empty_retry_notice = (
        files("biotasks.prompts").joinpath("worker-empty-response-retry.md").read_text()
        if response_recovery
        else None
    )
    generation_retry_notice = (
        files("biotasks.prompts").joinpath("worker-generation-retry.md").read_text()
        if response_recovery
        else None
    )
    missing_tool_retry_notice = (
        files("biotasks.prompts").joinpath("worker-missing-tool-retry.md").read_text()
        if response_recovery
        else None
    )
    root.mkdir(parents=True, exist_ok=False)
    identity = {
        "limits": asdict(limits),
        "max_requests": max_requests,
        "output_format": output_format,
        "context_recovery_sha256": hashlib.sha256(recovery_notice.encode()).hexdigest()
        if recovery_notice is not None
        else None,
        "runtime_budget_notice_sha256": hashlib.sha256(runtime_budget_notice.encode()).hexdigest()
        if runtime_budget_notice is not None
        else None,
        "empty_response_retry_sha256": hashlib.sha256(empty_retry_notice.encode()).hexdigest()
        if empty_retry_notice is not None
        else None,
        "generation_retry_sha256": hashlib.sha256(generation_retry_notice.encode()).hexdigest()
        if generation_retry_notice is not None
        else None,
        "missing_tool_retry_sha256": hashlib.sha256(missing_tool_retry_notice.encode()).hexdigest()
        if missing_tool_retry_notice is not None
        else None,
        "stage_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(
            files("biotasks").joinpath("chat_author.py").read_bytes()
        ).hexdigest(),
    }
    save_record(root / "input.json", context)
    (root / "system-prompt.md").write_text(prompt)
    author = GLMChatAuthor(
        complete=complete,
        save_record=save_record,
        ledger=ledger,
        scope=name,
        deadline=deadline,
        limits=limits,
        output_format=output_format,
        context_recovery_notice=recovery_notice,
        empty_response_retry_notice=empty_retry_notice,
        generation_retry_notice=generation_retry_notice,
        missing_tool_retry_notice=missing_tool_retry_notice,
        runtime_budget_notice=runtime_budget_notice,
    )

    async def run_author(**kwargs):
        try:
            return await author(**kwargs)
        except OutputTokenLimit as error:
            if not recover_output_limit:
                raise
            # The response is recorded and its request slot consumed. Upstream
            # permits one concise resubmission within the same stage allowance.
            # Transport errors and other incomplete responses remain terminal.
            raise ProviderOutputError(str(error)) from error

    return await artifact_stage(
        schema=schema,
        stage=name,
        inputs=context,
        system=prompt,
        prompt=json.dumps(context, ensure_ascii=False),
        root=root / "artifact-stage",
        budget=budget,
        model="glm-5.3",
        runtime="biotasks-glm-chat-v1",
        max_cost=1,
        max_turns=max_requests,
        deadline=deadline,
        validate=validate,
        shell=shell,
        shell_timeout_sec=shell_timeout_sec,
        extra_tools=extra_tools,
        extra_handlers=extra_handlers,
        agent_runner=run_author,
        agent_runner_identity=canonical_digest(identity),
    )
