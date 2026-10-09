"""Harbor agent adapter: pinned Pi on the host, native Pi tools in the sandbox.

Inference credentials are host-only. Runtime network denial is Harbor/Daytona's
responsibility and must be tested separately from this transport.
"""

import asyncio
import hmac
import json
import os
import secrets
import shlex
import signal
import tempfile
import time
from pathlib import Path

from aiohttp import web
from harbor.agents.base import BaseAgent

from biotasks.sandbox_tools import SandboxTools


class PiRemoteAgent(BaseAgent):
    SUPPORTS_ATIF = False  # Preserve raw Pi JSONL; do not advertise an untested converter.

    @staticmethod
    def name():
        return "pi-remote"

    def version(self):
        return "1.1.0"

    async def setup(self, environment):
        process = await asyncio.create_subprocess_exec(
            os.environ["BIOTASKS_PI_COMMAND"],
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), 15)
        if process.returncode or stdout.decode().strip().splitlines()[-1] != self.version():
            raise RuntimeError("Unexpected Pi version; expected 1.1.0")
        result = await environment.exec(command="pwd", timeout_sec=10)
        if result.return_code or not result.stdout.strip().startswith("/"):
            raise RuntimeError("Could not identify remote working directory")
        self.remote_cwd = result.stdout.strip()
        probe = Path(__file__).with_name("network_probe.py").read_text()
        result = await environment.exec(command="python3 -c " + shlex.quote(probe), timeout_sec=30)
        if result.return_code:
            raise RuntimeError("Could not complete task network/resource probe")
        evidence = json.loads(result.stdout)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "network-preflight.json").write_text(json.dumps(evidence, indent=2))
        if not evidence["network_denied"] or evidence["inference_credentials_present"]:
            raise RuntimeError("Task environment isolation preflight failed")
        if evidence["gpu_devices"]:
            raise RuntimeError("Unexpected task GPU device")

    async def run(self, instruction, environment, context):
        started = time.monotonic()
        transport = SandboxTools(environment.exec, started + 300)
        token = secrets.token_urlsafe(32)

        async def call(request):
            if not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + token):
                raise web.HTTPForbidden()
            try:
                result = await transport.dispatch(await request.json())
                return web.json_response(result)
            except (ValueError, RuntimeError, TimeoutError) as error:
                return web.json_response({"error": str(error)}, status=400)

        app = web.Application(client_max_size=128 * 1024)
        app.router.add_post("/tools", call)
        runner = web.AppRunner(app, access_log=None, shutdown_timeout=1)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        address = runner.addresses[0]
        process = None
        try:
            with tempfile.TemporaryDirectory(prefix="biotasks-pi-") as temporary:
                root = Path(temporary)
                state = root / "state"
                state.mkdir()
                work = root / "work"
                work.mkdir()
                provider = {
                    "baseUrl": os.environ["GLM_API_BASE"],
                    "api": "openai-completions",
                    "apiKey": "BIOTASKS_MODEL_KEY",
                    "compat": {
                        "supportsDeveloperRole": False,
                        "supportsReasoningEffort": False,
                        "requiresReasoningContentOnAssistantMessages": True,
                        "thinkingFormat": "chat-template",
                        "chatTemplateKwargs": {"enable_thinking": {"$var": "thinking.enabled"}},
                    },
                    "models": [
                        {
                            "id": "glm-5.3",
                            "name": "glm-5.3",
                            "reasoning": True,
                            "input": ["text"],
                            "contextWindow": 131072,
                            "maxTokens": 16384,
                            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                        }
                    ],
                }
                (state / "models.json").write_text(
                    json.dumps({"providers": {"biotasks": provider}})
                )
                (state / "settings.json").write_text(
                    json.dumps(
                        {
                            "retry": {"enabled": False},
                            "compaction": {
                                "enabled": True,
                                "reserveTokens": 16384,
                                "keepRecentTokens": 16384,
                            },
                        }
                    )
                )
                # Pass only host-runtime settings, never the orchestrator's full environment.
                env = {
                    k: os.environ[k]
                    for k in ("PATH", "LANG", "LC_ALL", "TMPDIR")
                    if k in os.environ
                }
                env.update(
                    {
                        "PI_CODING_AGENT_DIR": str(state),
                        "BIOTASKS_MODEL_KEY": os.environ["GLM_BULK_TOKEN"],
                        "BIOTASKS_TOOL_ENDPOINT": f"http://{address[0]}:{address[1]}/tools",
                        "BIOTASKS_TOOL_TOKEN": token,
                        "BIOTASKS_REMOTE_CWD": self.remote_cwd,
                    }
                )
                command = [
                    os.environ["BIOTASKS_PI_COMMAND"],
                    "--provider",
                    "biotasks",
                    "--model",
                    "glm-5.3",
                    "--thinking",
                    "medium",
                    "--mode",
                    "json",
                    "--no-session",
                    "--no-extensions",
                    "--no-mcp",
                    "--no-skills",
                    "--no-prompt-templates",
                    "--no-context-files",
                    "--no-themes",
                    "--no-tools",
                    "--tools",
                    "sandbox_read,sandbox_bash,sandbox_edit,sandbox_write",
                    "--extension",
                    str(Path(__file__).with_name("pi_remote.ts")),
                    "--print",
                    instruction,
                ]
                with (root / "pi.jsonl").open("wb") as out, (root / "stderr.txt").open("wb") as err:
                    process = await asyncio.create_subprocess_exec(
                        *command, cwd=work, env=env, stdout=out, stderr=err, start_new_session=True
                    )
                    try:
                        await asyncio.wait_for(
                            process.wait(), max(0.1, 300 - (time.monotonic() - started))
                        )
                    finally:
                        if process.returncode is None:
                            os.killpg(process.pid, signal.SIGKILL)
                            await process.wait()
                        self.logs_dir.mkdir(parents=True, exist_ok=True)
                        for source, target in [
                            ("pi.jsonl", "pi.txt"),
                            ("stderr.txt", "pi-stderr.txt"),
                        ]:
                            # Input env is excluded; scrub known secrets defensively in tool/runtime errors.
                            value = (root / source).read_text(errors="replace")
                            for secret in (token, os.environ["GLM_BULK_TOKEN"]):
                                value = value.replace(secret, "[REDACTED]")
                            (self.logs_dir / target).write_text(value)
                if process.returncode:
                    raise RuntimeError(
                        f"Pi exited with code {process.returncode}; see preserved stderr"
                    )
                # Pi can exit zero after a provider error; Harbor's installed adapter
                # also checks the final assistant stop reason rather than trusting exit.
                last_assistant = None
                for line in (self.logs_dir / "pi.txt").read_text().splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if (
                        event.get("type") == "message_end"
                        and event.get("message", {}).get("role") == "assistant"
                    ):
                        last_assistant = event["message"]
                if last_assistant is None or last_assistant.get("stopReason") == "error":
                    raise RuntimeError(
                        "Pi did not finish a valid assistant response; see preserved trace"
                    )
        finally:
            await runner.cleanup()
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            (self.logs_dir / "transport.json").write_text(json.dumps(transport.records, indent=2))
            context.metadata = {
                "harness": "pi",
                "version": self.version(),
                "transport": "harbor-remote-tools",
                "agent_seconds": time.monotonic() - started,
                "task_inference_credentials": False,
            }
            self.populate_context_post_run(context)

    def populate_context_post_run(self, context):
        path = self.logs_dir / "pi.txt"
        if not path.exists():
            return
        usages = []
        for line in path.read_text().splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if (
                record.get("type") == "message_end"
                and record.get("message", {}).get("role") == "assistant"
            ):
                usages.append(record["message"].get("usage", {}))
        context.n_input_tokens = sum(
            u.get("input", 0) + u.get("cacheRead", 0) + u.get("cacheWrite", 0) for u in usages
        )
        context.n_output_tokens = sum(u.get("output", 0) for u in usages)
        context.n_cache_tokens = sum(u.get("cacheRead", 0) for u in usages)
        context.cost_usd = 0.0  # Existing free service; excludes orchestration/sandbox charges.
