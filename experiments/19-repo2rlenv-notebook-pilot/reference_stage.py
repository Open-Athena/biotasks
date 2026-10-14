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
):
    """Use upstream's one output recovery, never retry an uncertain transport."""
    prompt = files("biotasks.prompts").joinpath(prompt_name + ".md").read_text()
    root.mkdir(parents=True, exist_ok=False)
    identity = {
        "limits": asdict(limits),
        "max_requests": max_requests,
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
        agent_runner=run_author,
        agent_runner_identity=canonical_digest(identity),
    )
