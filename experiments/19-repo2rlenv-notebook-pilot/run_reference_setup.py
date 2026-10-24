"""One tool-enabled GLM setup session and controlled offline reference tests.

Run on Iris; all generated commands run in a disposable Daytona sandbox.
The retired combined runner is deliberately not re-enabled.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import httpx
from daytona import CreateSandboxFromImageParams, Daytona, Resources
from design_stage import completion_transport
from model_profile import native_effort
from openai import AsyncOpenAI
from preflight import PROBE, TARGETS
from reference_setup import (
    TEST_TOOL,
    PreparedReference,
    SetupBudgetExceeded,
    SetupOutcome,
    SetupSession,
)
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.daytona import DaytonaWorker
from repo2rlenv.execution.daytona_cleanup import cleanup
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.execution.read_retry import transient_connection_error
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger

HERE = Path(__file__).parent
# The wrapper may run for seconds+10, then terminate for5seconds. The SDK
# execution wait is seconds+25 and its HTTP timeout adds5seconds. Leave a
# further25seconds for receipt/log reconciliation inside the campaign deadline.
COMMAND_RETURN_ALLOWANCE_SECONDS = 55


def check_config(config):
    native_effort(config)
    if "allow_quality_repair" in config and type(config["allow_quality_repair"]) is not bool:
        raise ValueError("allow_quality_repair must be boolean")
    if "inspect_review_evidence" in config and type(config["inspect_review_evidence"]) is not bool:
        raise ValueError("inspect_review_evidence must be boolean")
    if config.get("entrypoint") not in {
        "run_reference_setup.py",
        "run_reference_replay.py",
        "run_notebook_grader.py",
    }:
        raise ValueError("Use the separate reference-setup entry point")
    grading = config["entrypoint"] == "run_notebook_grader.py"
    if "review_observation_directories" in config:
        roots = config["review_observation_directories"]
        if (
            not grading
            or config.get("inspect_review_evidence") is not True
            or not isinstance(roots, list)
            or any(
                not isinstance(name, str)
                or not name
                or name == "."
                or Path(name).is_absolute()
                or ".." in Path(name).parts
                or Path(name).as_posix() != name
                for name in roots
            )
        ):
            raise ValueError("Review observation directories require explicit local reviewer roots")
    recovery_keys = (
        "resume_grading_directory",
        "resume_grader_draft_directory",
        "resume_independent_directory",
    )
    if sum(bool(config.get(key)) for key in recovery_keys) > 1:
        raise ValueError("Select one grading recovery mode")
    if config.get("independent_repair_file") and (
        not grading
        or not config.get("frozen_grader_file")
        or config.get("allow_quality_repair", True)
        or any(config.get(key) for key in recovery_keys)
    ):
        raise ValueError(
            "Independent repair requires fresh grading, frozen science and no extra repair"
        )
    if config.get("resume_probe_draft_directory") and (
        not config.get("resume_grading_directory") or config.get("resume_probes_directory")
    ):
        raise ValueError(
            "Probe draft repair requires full grader recovery and no frozen probe resume"
        )
    if grading:
        if config.get("max_tests", "missing") is not None or config.get("verifier_seconds") != 120:
            raise ValueError("Grading uses time-bounded checks and the agreed 120-second verifier")
    elif type(config.get("max_tests")) is not int or config["max_tests"] < 1:
        raise ValueError("Explicit agreed max_tests is required before execution")
    for name in (
        "setup_seconds",
        "reference_seconds",
        "campaign_seconds",
        "cleanup_seconds",
        "request_timeout_seconds",
    ):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f"Explicit agreed {name} is required before execution")
    if "max_requests" not in config or config["max_requests"] is not None:
        raise ValueError("Setup uses explicit null max_requests: no request-count cap")
    if config["reference_seconds"] != 600:
        raise ValueError("The current reference computation allowance is 600 seconds")
    if config["campaign_seconds"] <= config["cleanup_seconds"]:
        raise ValueError("Campaign must leave time for cleanup")
    if not 0 < float(config["daytona_budget_usd"]) <= 100:
        raise ValueError("A positive reservation within the standing spending ceiling is required")
    for key in (
        "preparation_directory",
        "reference_directory",
        "replay_directory",
        "specification_directory",
        "materialization_directory",
        "resume_grading_directory",
        "resume_grader_draft_directory",
        "resume_independent_directory",
        "resume_probes_directory",
        "resume_probe_draft_directory",
        "resume_contract_directory",
        "contract_feedback_file",
        "frozen_grader_file",
        "independent_repair_file",
    ):
        if key in config and (
            not config[key] or Path(config[key]).is_absolute() or ".." in Path(config[key]).parts
        ):
            raise ValueError("Input directories must be checkpoint-relative")
    directory = Path(config["preparation_directory"])
    if directory.is_absolute() or ".." in directory.parts:
        raise ValueError("Preparation must be within the frozen experiment")


class OperationBudgetExceeded(TimeoutError):
    """A command was refused before dispatch; no remote outcome is uncertain."""

    def __init__(self, available_seconds):
        self.available_seconds = available_seconds
        super().__init__("Insufficient time for the full operation and its return")


class Remote:
    """Recorded, timeout-bounded I/O using upstream DaytonaWorker."""

    def __init__(self, worker, sandbox, root, deadline, cpus, *, session_process=None):
        self.worker, self.sandbox, self.root = worker, sandbox, root
        self.deadline, self.cpus = deadline, cpus
        self.session_process = session_process
        self.uncertain = False
        self.operation = 0

    def remaining(self, requested):
        if self.uncertain:
            raise RuntimeError(
                "Remote operation outcome uncertain; cleanup/reconciliation required"
            )
        remaining = int(self.deadline - time.time()) - 15
        if requested > remaining:
            raise OperationBudgetExceeded(remaining)
        return requested

    async def upload(self, local, remote):
        await asyncio.to_thread(self.worker.upload, local, remote)

    async def download(self, remote, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self.worker.download, remote, local)

    async def command(self, argv, seconds, label, *, cwd="/work"):
        self.remaining(seconds)
        self.operation += 1
        directory = self.root / "operations" / f"{self.operation:04d}"
        directory.mkdir(parents=True)
        remote_label = "command-" + uuid.uuid4().hex
        record = {
            "argv": argv,
            "seconds": seconds,
            "label": label,
            "state": "uncertain",
            "started": time.time(),
            "remote_label": remote_label,
            "reconciliation_deadline": min(
                self.deadline - 15, time.time() + seconds + COMMAND_RETURN_ALLOWANCE_SECONDS
            ),
        }
        save_record(directory / "operation.json", record)
        # Generated setup may overwrite files; reinstall the controller's runner.
        await self.upload(HERE / "reference_remote.py", "/work/remote.py")
        self.uncertain = True
        env = [
            "env",
            *[
                f"{name}={self.cpus}"
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "POLARS_MAX_THREADS",
                    "RAYON_NUM_THREADS",
                )
            ],
        ]

        async def verified_output(process):
            if (
                not isinstance(process, dict)
                or process.get("argv") != argv
                or process.get("directory") != cwd
                or process.get("label") != remote_label
                or process.get("timeout_seconds") != seconds
                or type(process.get("exit_code")) is not int
                or type(process.get("timed_out")) is not bool
                or not isinstance(process.get("log_sha256"), str)
            ):
                raise ValueError("Remote completion receipt differs from this operation")
            await self.download("/work/logs/" + remote_label + ".log", directory / "output.log")
            with (directory / "output.log").open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != process["log_sha256"]:
                    raise ValueError("Remote completion log checksum mismatch")
            return {**process, "log": (directory / "output.log").read_text(errors="replace")}

        try:
            try:
                command = [
                    *env,
                    "timeout",
                    "--signal=TERM",
                    "--kill-after=5",
                    str(seconds + 10),
                    "python",
                    "/work/remote.py",
                    "execute",
                    json.dumps(argv),
                    str(seconds),
                    cwd,
                    remote_label,
                ]
                if self.session_process is not None:
                    from daytona_session import session_command

                    result = await session_command(
                        self.session_process,
                        command,
                        timeout=seconds + 25,
                        directory=directory,
                    )
                else:
                    result = await asyncio.to_thread(
                        self.worker.exec, command, timeout=seconds + 25
                    )
                if result.returncode:
                    # A failed wrapper may never produce a completion receipt.
                    # Keep its actual response in the private evidence store;
                    # exception messages must not expose arbitrary command output.
                    save_record(
                        directory / "controller-result.json",
                        {
                            "returncode": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                        },
                    )
                    record["controller_failure"] = {
                        "returncode": result.returncode,
                        "result_path": "controller-result.json",
                    }
                result.checked("Reference controller operation")
                process = json.loads(result.stdout)
                output = await verified_output(process)
            except Exception as error:
                if not transient_connection_error(error):
                    raise
                try:
                    remaining = record["reconciliation_deadline"] - time.time()
                    if remaining <= 0:
                        raise TimeoutError("No remaining time for completion reconciliation")
                    async with asyncio.timeout(remaining):
                        receipt = directory / "recovered-process.json"
                        await self.download("/work/logs/" + remote_label + ".json", receipt)
                        process = json.loads(receipt.read_text())
                        output = await verified_output(process)
                except Exception as recovery_error:
                    record["recovery_error_type"] = type(recovery_error).__name__
                    raise error from None
                record["transport_recovery"] = {
                    "error_type": type(error).__name__,
                    "completion_receipt_verified": True,
                    "command_reexecuted": False,
                }
            self.uncertain = False
            record.update(state="returned", process=process, finished=time.time())
            save_record(directory / "operation.json", record)
            return output
        except BaseException as error:
            record.update(error_type=type(error).__name__, finished=time.time())
            save_record(directory / "operation.json", record)
            raise

    async def helper(self, args, label):
        # Every invocation restores the helper from controller-owned source.
        result = await self.command(["python", "/work/remote.py", *args], 120, label)
        if result["exit_code"]:
            raise RuntimeError("Controller evidence check failed; inspect the preserved log")
        return json.loads(result["log"])

    async def network(self, blocked):
        self.remaining(45)
        control_deadline = min(time.time() + 45, self.deadline - 15)
        path = self.root / "network" / ("control-" + uuid.uuid4().hex + ".json")
        record = {
            "blocked": blocked,
            "started": time.time(),
            "control_deadline": control_deadline,
            "state": "uncertain",
            "events": [],
        }
        save_record(path, record)
        self.uncertain = True

        async def control(kind, **kwargs):
            seconds = min(
                30 if kind == "update_network_settings" else 15, int(control_deadline - time.time())
            )
            if seconds < 1:
                raise TimeoutError("Network reconciliation exhausted its original allowance")
            event = {"operation": kind, "request_timeout": seconds, "started": time.time()}
            record["events"].append(event)
            save_record(path, record)
            try:
                await asyncio.to_thread(
                    getattr(self.sandbox, kind), request_timeout=seconds, **kwargs
                )
            except BaseException as error:
                event["error_type"] = type(error).__name__
                raise
            finally:
                event["finished"] = time.time()
                save_record(path, record)
            if time.time() >= control_deadline:
                raise TimeoutError("Network response arrived after its original allowance")

        def recoverable(error):
            return getattr(error, "status_code", None) not in {401, 403} and (
                transient_connection_error(error)
            )

        async def read_state():
            for attempt in range(2):
                try:
                    await control("refresh_data")
                    observed = self.sandbox.network_block_all
                    if type(observed) is not bool:
                        raise RuntimeError("Provider did not return a boolean network policy")
                    record["events"][-1]["observed_blocked"] = observed
                    save_record(path, record)
                    return observed
                except Exception as error:
                    if attempt or not recoverable(error):
                        raise

        try:
            try:
                await control("update_network_settings", network_block_all=blocked)
            except Exception as error:
                if not recoverable(error):
                    raise
                # Only the same idempotent provider setting may be repeated. Read
                # first: a lost response can still mean the update took effect.
                if await read_state() is not blocked:
                    try:
                        await control("update_network_settings", network_block_all=blocked)
                    except Exception as retry_error:
                        if not recoverable(retry_error):
                            raise
                    if await read_state() is not blocked:
                        raise RuntimeError("Provider network policy remains unconfirmed") from None
            else:
                if await read_state() is not blocked:
                    raise RuntimeError("Provider network policy differs from requested state")
            self.uncertain = False
            result = await self.command(
                ["python", "-c", "TARGETS = " + repr(TARGETS) + "\n" + PROBE],
                30,
                f"network-{self.operation}",
            )
            probes = json.loads(result["log"])
            record["probes"] = probes
            if result["exit_code"] or probes != [
                {"host": h, "port": p, "reachable": not blocked} for h, p in TARGETS
            ]:
                raise RuntimeError("Network probe did not establish the required state")
            record.update(
                state="verified",
                limitations="Representative outbound TCP probes, not exhaustive attestation",
            )
        except BaseException as error:
            self.uncertain = True
            record["error_type"] = type(error).__name__
            raise
        finally:
            record["finished"] = time.time()
            save_record(path, record)


async def run(
    config,
    *,
    root,
    deadline,
    endpoint,
    credential,
    provider=None,
    complete=None,
    repair_exports=None,
):
    config = {**config, "reasoning_effort": native_effort(config)}
    check_config(config)
    prepared = PreparedReference.load(HERE / config["preparation_directory"])
    target = prepared.context["limits"]
    if target.get("gpu") is not False:
        raise ValueError("This execution profile is CPU-only")
    if config["reference_seconds"] != target["reference_seconds"]:
        raise ValueError("Reference allowance differs from the reviewed preparation")
    replay = config["entrypoint"] == "run_reference_replay.py"
    grading = config["entrypoint"] == "run_notebook_grader.py"
    if replay or grading:
        from reference_replay import load_snapshot, replay_reference

        snapshot = load_snapshot(HERE / config["reference_directory"], prepared)
        if grading and config.get("materialization_directory"):
            from materialization_inputs import load_materialized

            candidate, derived = load_materialized(HERE / config["materialization_directory"])
            snapshot = {
                **snapshot,
                "outputs": derived["reference"],
                "materialization": {"candidate": candidate, "execution": derived},
                "restored_outputs_root": "/work/grading-inputs/grading/materialized/reference",
            }
    root.mkdir(parents=True, exist_ok=False)
    save_record(root / "configuration.json", config)
    save_record(root / "preparation-input.json", prepared.context)
    result = {
        "status": "started",
        "started": time.time(),
        "construction_run": False,
        "solver_run": False,
        "semantic_fidelity_validated": False,
        "cleanup_verified": False,
    }
    provider = provider or Daytona()
    client = None
    owner = config["campaign"]
    created, creation_started = False, False
    work_deadline = (
        min(deadline, time.time() + config["campaign_seconds"]) - config["cleanup_seconds"]
    )
    try:
        reservation = BudgetLedger(
            root / "daytona-budget.sqlite", limit_usd=config["daytona_budget_usd"]
        )
        reservation.reserve(
            owner,
            config["daytona_budget_usd"],
            "Full setup campaign reservation; not measured cost",
        )
        save_record(root / "sandbox-claim.json", {"owner": owner, "state": "creation_uncertain"})
        creation_started = True
        sandbox = await asyncio.to_thread(
            provider.create,
            CreateSandboxFromImageParams(
                name="biotasks19-" + owner,
                image=target["base_image"],
                language="python",
                os_user="root",
                resources=Resources(
                    cpu=target["task_cpus"],
                    memory=target["task_memory_gib"],
                    disk=target["task_disk_gib"],
                ),
                labels={"repo2rlenv.job": owner},
                auto_stop_interval=30,
                auto_delete_interval=0,
                ttl_minutes=(config["campaign_seconds"] + config["cleanup_seconds"] + 59) // 60,
                public=False,
            ),
            timeout=420,
        )
        created = True
        await asyncio.to_thread(sandbox.refresh_data, request_timeout=15)
        resources = {key: getattr(sandbox, key) for key in ("cpu", "memory", "disk")}
        save_record(
            root / "sandbox-claim.json",
            {"owner": owner, "id": sandbox.id, "state": "created", "resources": resources},
        )
        if resources != {
            "cpu": target["task_cpus"],
            "memory": target["task_memory_gib"],
            "disk": target["task_disk_gib"],
        }:
            raise RuntimeError("Provider resource envelope mismatch")
        worker = DaytonaWorker(provider, sandbox)
        # Provision only the controller's working directory before its runner exists.
        (
            await asyncio.to_thread(worker.exec, ["mkdir", "-p", "/work", "/work/logs"], timeout=30)
        ).checked("Initialize controller directory")
        remote = Remote(worker, sandbox, root, work_deadline, target["task_cpus"])
        if grading:
            from grading_session import run_grading

            result.update(
                await run_grading(
                    remote=remote,
                    snapshot=snapshot,
                    root=root,
                    config=config,
                    endpoint=endpoint,
                    credential=credential,
                    deadline=work_deadline,
                    complete=complete,
                )
            )
        elif replay:
            RequestLedger(root / "requests.sqlite", {"setup": Allowance(None, None)})
            result.update(
                await replay_reference(
                    remote=remote,
                    snapshot=snapshot,
                    root=root / "replay",
                    config=config,
                )
            )
        else:
            ledger = RequestLedger(
                root / "requests.sqlite", {"setup": Allowance(config["max_requests"], None)}
            )
            spend = RunBudget(
                BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "setup", "1"
            )

            async def bounded_repair(feedback):
                async with asyncio.timeout(max(0, work_deadline - time.time())):
                    return await repair_exports(feedback, deadline=work_deadline)

            session = SetupSession(
                prepared=prepared,
                remote=remote,
                root=root / "setup",
                setup_seconds=config["setup_seconds"],
                reference_seconds=config["reference_seconds"],
                max_tests=config["max_tests"],
                repair_exports=bounded_repair if repair_exports is not None else None,
            )
            await session.initialize()
            from reference_setup import import_inventory

            context = {
                "source_imports": {
                    "analysis": import_inventory(prepared.baseline),
                    "exports": import_inventory(prepared.exports),
                    "scope": "Literal source statements and locations only; dynamic imports, native libraries and availability remain unverified.",
                },
                "preparation": {
                    "source": prepared.context["source"],
                    "conversion": prepared.context["conversion"],
                    "plan": prepared.plan.model_dump(),
                },
                "paths": {
                    "original.py": "/work/frozen/original.py",
                    "exports.py": "/work/frozen/exports.py",
                    "plan.json": "/work/frozen/plan.json",
                    "setup": "/work/setup",
                    "reference_cwd": "/work/run",
                },
                "limits": {
                    **target,
                    **{
                        k: config[k]
                        for k in (
                            "max_requests",
                            "max_tests",
                            "setup_seconds",
                            "reference_seconds",
                            "campaign_seconds",
                            "request_timeout_seconds",
                        )
                    },
                },
            }
            limits = ChatLimits(
                max_output_tokens=None,
                max_input_bytes=None,
                max_response_bytes=None,
                tool_output_chars=None,
                reasoning_effort=native_effort(config),
                request_timeout_sec=config["request_timeout_seconds"],
            )
            if complete is None:
                client = AsyncOpenAI(
                    base_url=endpoint,
                    api_key=credential,
                    max_retries=0,
                    timeout=limits.request_timeout_sec,
                    http_client=httpx.AsyncClient(follow_redirects=False),
                )
                complete = completion_transport(client)
            outcome = await stage(
                schema=SetupOutcome,
                name="setup",
                prompt_name="notebook-reference-setup",
                context=context,
                root=root / "worker",
                ledger=ledger,
                budget=AuthorBudget(spend, root / "charges", "setup"),
                complete=complete,
                deadline=work_deadline,
                limits=limits,
                max_requests=config["max_requests"],
                validate=session.validate_outcome,
                recover_output_limit=False,
                shell=session.shell,
                extra_tools=[TEST_TOOL],
                extra_handlers={"test_reference": session.test_reference},
            )
            save_record(root / "outcome.json", outcome.model_dump())
            result.update(
                status="reference_executed_requires_review"
                if outcome.disposition == "tested"
                else "worker_blocked",
                reference_tests=session.tests,
                reference_test_requests=session.test_requests,
                setup_seconds_remaining=session.setup_remaining,
                last_passing_test=session.last_pass,
                effective_frozen_directory=session.frozen.relative_to(root).as_posix(),
                effective_preparation_directory=str(session.effective_preparation)
                if session.effective_preparation is not None
                else None,
            )
            if (
                outcome.disposition == "blocked"
                and session.tests == 0
                and session.setup_remaining < 1
            ):
                # A setup/tool transport stall can spend the whole allowance
                # before scientific dispatch. Preserve the worker's outcome,
                # but never turn that lack of execution into a seed rejection.
                result["incomplete_reason"] = "setup_budget_exhausted_before_reference"
                raise SetupBudgetExceeded(
                    "Setup allowance exhausted before any controlled reference dispatch"
                )
    except BaseException as error:
        result.update(status="incomplete", error_type=type(error).__name__)
        raise
    finally:
        try:
            if client is not None:
                await client.close()
            result["finished"] = time.time()
            save_record(root / "result.json", result)
            from iris_bootstrap import export_on_host

            await asyncio.to_thread(
                export_on_host,
                root,
                os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
                + (
                    "/grading" if grading else "/reference-replay" if replay else "/reference-setup"
                ),
                deadline=deadline - config["cleanup_seconds"],
            )
        finally:
            try:
                cleaned = (
                    await asyncio.to_thread(cleanup, owner, provider)
                    if creation_started
                    else {"passed": True}
                )
                result["cleanup_verified"] = cleaned["passed"] and (not creation_started or created)
                save_record(root / "cleanup.json", cleaned)
            finally:
                result["finished"] = time.time()
                save_record(root / "result.json", result)
    if not result["cleanup_verified"]:
        raise RuntimeError("Owned sandbox cleanup needs reconciliation")
    return result


if __name__ == "__main__":
    asyncio.run(
        run(
            json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text()),
            root=Path("/evidence/reference-setup"),
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
        )
    )
