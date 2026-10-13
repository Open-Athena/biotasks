"""Design-only integration with Tasksmith's artifact stage and SETA's schema.

The launcher owns a prepared remote workspace, input profiling and cleanup.
Calling this entry point never invokes the builder, quality loop or solver.
Dependencies come from the experiment's pinned upstream environment.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import shlex
import time
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from openai import AsyncOpenAI
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.seta_seed2synth.recipe import TaskDesign
from repo2rlenv.tasksmith.author.artifact import artifact_stage, canonical_digest

from biotasks.chat_author import ChatLimits, GLMChatAuthor
from biotasks.inference_gate import Allowance, RequestLedger


def remote_shell(worker, *, directory: str, deadline: float, total_seconds: int = 300):
    """Controller callback using upstream's remote worker, with no local fallback."""
    if type(total_seconds) is not int or total_seconds < 1:
        raise ValueError("A positive cumulative tool-time ceiling is required")
    remaining_tools = total_seconds

    async def shell(command: str, timeout_sec: int = 120):
        nonlocal remaining_tools
        if not isinstance(command, str) or not 0 < len(command) <= 12000:
            raise ValueError("A bounded command string is required")
        if type(timeout_sec) is not int or not 1 <= timeout_sec <= 120:
            raise ValueError("Tool timeout must be between 1 and 120 seconds")
        permitted = min(timeout_sec, remaining_tools, int(deadline - time.time()) - 10)
        if permitted <= 0:
            return "Inspection budget exhausted. Submit the supported design or report a blocker."
        remaining_tools -= permitted
        started = time.monotonic()
        try:
            result = await asyncio.to_thread(
                worker.exec,
                [
                    "timeout",
                    "--signal=TERM",
                    "--kill-after=5",
                    f"{permitted}s",
                    "sh",
                    "-c",
                    "cd " + shlex.quote(directory) + " && " + command,
                ],
                timeout=permitted + 10,
            )
        except Exception:
            # Provider errors can include private routes. The owning launcher
            # must reconcile this worker, not retry a possibly running command.
            raise RuntimeError(
                "Remote inspection outcome is uncertain; reconcile the owned worker"
            ) from None
        # Definite completion releases unused time. A lost result retains the
        # full ceiling and ends the stage; it must not dispatch a replacement.
        remaining_tools += max(0, permitted - max(1, math.ceil(time.monotonic() - started)))
        return json.dumps(
            {
                "returncode": result.returncode,
                "stdout": result.stdout[:16000],
                "stderr": result.stderr[:4000],
                "truncated": len(result.stdout) > 16000 or len(result.stderr) > 4000,
                "remaining_tool_seconds": remaining_tools,
            }
        )

    return shell


def completion_transport(client):
    async def complete(payload):
        options = dict(payload)
        extension = options.pop("chat_template_kwargs")
        response = await client.chat.completions.create(
            **options, extra_body={"chat_template_kwargs": extension}
        )
        return response.model_dump(mode="json")

    return complete


async def design_notebook(
    *,
    seed: dict,
    profile: dict,
    workspace: dict,
    worker,
    root: Path,
    endpoint: str,
    credential: str,
    budget,
    deadline: float,
    max_requests: int,
    limits: ChatLimits,
    max_tool_seconds: int = 300,
    complete=None,
):
    route = urlsplit(endpoint)
    if (
        route.scheme not in {"http", "https"}
        or not route.hostname
        or route.username
        or route.password
        or route.query
        or route.fragment
        or not credential
    ):
        raise ValueError("A credential and plain HTTP(S) model base URL are required")
    if type(max_requests) is not int or not 3 <= max_requests <= 80:
        raise ValueError("Specify a design-stage request ceiling between 3 and 80")
    if profile.get("scientific_analysis_executed") is not False or not profile.get("files"):
        raise ValueError("An explicit factual input profile is required")
    if not workspace.get("inputs") or not workspace.get("scratch"):
        raise ValueError("Identify prepared inputs and a separate scratch workspace")
    if workspace["inputs"] == workspace["scratch"]:
        raise ValueError("Inputs and scratch must be separate directories")
    if type(max_tool_seconds) is not int or max_tool_seconds < 1:
        raise ValueError("Specify a positive cumulative inspection ceiling")
    prompt = files("biotasks.prompts").joinpath("notebook-task-design.md").read_text()
    root.mkdir(parents=True, exist_ok=True)
    requests = RequestLedger(
        root / "requests.sqlite",
        {"design": Allowance(requests=max_requests, output_tokens=limits.max_output_tokens)},
    )
    identity = {
        "adapter_sha256": hashlib.sha256(
            files("biotasks").joinpath("chat_author.py").read_bytes()
        ).hexdigest(),
        "stage_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "endpoint_sha256": hashlib.sha256(endpoint.encode()).hexdigest(),
        "limits": asdict(limits),
        "max_requests": max_requests,
        "max_tool_seconds": max_tool_seconds,
    }
    context = {"seed": seed, "input_profile": profile, "workspace": workspace, "limits": identity}
    input_path, prompt_path = root / "input.json", root / "system-prompt.md"
    if input_path.exists() and json.loads(input_path.read_text()) != context:
        raise ValueError("Retained design inputs differ; use a new run directory")
    if prompt_path.exists() and prompt_path.read_text() != prompt:
        raise ValueError("Retained design prompt differs; use a new run directory")
    if not input_path.exists():
        save_record(input_path, context)
    if not prompt_path.exists():
        prompt_path.write_text(prompt)
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
        author = GLMChatAuthor(
            complete=complete,
            save_record=save_record,
            ledger=requests,
            scope="design",
            deadline=deadline,
            limits=limits,
        )
        design = await artifact_stage(
            schema=TaskDesign,
            stage="notebook-design",
            inputs=context,
            system=prompt,
            prompt=json.dumps(context, ensure_ascii=False),
            root=root / "stage",
            budget=budget,
            model="glm-5.3",
            runtime="biotasks-glm-chat-v1",
            max_cost=1,
            max_turns=max_requests,
            deadline=deadline,
            shell=remote_shell(
                worker,
                directory=workspace["scratch"],
                deadline=deadline,
                total_seconds=max_tool_seconds,
            ),
            agent_runner=author,
            agent_runner_identity=canonical_digest(identity),
        )
        save_record(
            root / "design-result.json",
            {
                "status": "submitted_for_review",
                "design": design.model_dump(),
                "scientifically_validated": False,
                "construction_run": False,
            },
        )
        return design
    finally:
        if client is not None:
            await client.close()
