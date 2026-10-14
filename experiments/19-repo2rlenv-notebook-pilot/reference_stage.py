"""Reference preparation/review using the pinned Tasksmith artifact controller."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.tasksmith.author.artifact import artifact_stage, canonical_digest

from biotasks.chat_author import GLMChatAuthor


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
):
    """One bounded stage; no automatic provider retry or hidden task edits."""
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
        agent_runner=author,
        agent_runner_identity=canonical_digest(identity),
    )
