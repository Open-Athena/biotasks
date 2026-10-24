"""An explicitly launched infrastructure check, never a notebook/model run.

The operator must first reserve funding and an actual free shared-pool slot.
No network calls occur at import. Keep configuration/results in the private
handoff; preserve the frozen script/config and the original cleanup evidence.
"""

import argparse
import asyncio
import importlib.metadata
import json
import re
import sys
import time
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))

from daytona import AsyncDaytona, CreateSandboxFromImageParams, Daytona, Resources  # noqa: E402
from repo2rlenv.execution.daytona import DaytonaWorker  # noqa: E402
from repo2rlenv.execution.daytona_cleanup import cleanup  # noqa: E402
from repo2rlenv.execution.lifecycle import save_record  # noqa: E402
from run_reference_setup import Remote  # noqa: E402


class LoseAcknowledgement:
    """Inject one client-side loss only after the submitted command completed."""

    def __init__(self, process, evidence, deadline):
        self.process, self.evidence, self.deadline = process, evidence, deadline

    def __getattr__(self, name):
        return getattr(self.process, name)

    async def execute_session_command(self, session, request, **kwargs):
        response = await self.process.execute_session_command(session, request, **kwargs)

        async def discard(_chunk):
            pass

        async with asyncio.timeout(max(0, self.deadline - time.time())):
            observed = await self.process.get_session_command(
                session, response.cmd_id, request_timeout=15
            )
            if observed.exit_code is None:
                await self.process.get_session_command_logs_async(
                    session, response.cmd_id, discard, discard
                )
                observed = await self.process.get_session_command(
                    session, response.cmd_id, request_timeout=15
                )
        if (
            observed.id != response.cmd_id
            or observed.command != request.command
            or type(observed.exit_code) is not int
        ):
            raise RuntimeError("Cannot inject loss without original command completion")
        save_record(
            self.evidence,
            {
                "session_id": session,
                "command_id": response.cmd_id,
                "original_command_completed_before_injection": True,
                "injected_acknowledgement_loss": True,
                "command_reexecuted": False,
            },
        )
        raise ConnectionError("Injected acknowledgement loss after original completion")


def program(name, exit_code):
    # Each execution appends one small record; no read/modify/write counter race.
    return (
        "import json,os,time\n"
        f"fd=os.open('/work/probe-counts/{name}.txt',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)\n"
        "os.write(fd,b'ran\\n');os.close(fd)\n"
        "time.sleep(1)\n"
        f"print(json.dumps({{'case':{name!r},'synthetic':True}}))\n"
        f"raise SystemExit({exit_code})\n"
    )


async def run(config, root):
    if (
        not re.fullmatch(r"biotasks19-session-compat-[a-z0-9-]+", config["owner"])
        or config["resources"] != {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False}
        or config["seconds"] != 300
        or config["cleanup_seconds"] != 180
        or config["reservation_usd"] != "1.00"
        or config["model_calls"] != 0
        or importlib.metadata.version("daytona") != "0.211.2"
    ):
        raise ValueError("Compatibility check differs from its recorded execution profile")
    root.mkdir(parents=True, exist_ok=False)
    save_record(root / "configuration.json", config)
    owner = config["owner"]
    provider, async_client = Daytona(), AsyncDaytona()
    work_deadline = time.time() + config["seconds"]
    result = {
        "status": "incomplete",
        "started": time.time(),
        "cases": [],
        "new_model_calls": 0,
        "scientific_computation": False,
        "cleanup_verified": False,
        "synthetic_failure_injection": "One acknowledged original completion is hidden from the caller; this is not a naturally occurring provider failure.",
    }
    created = False
    primary = None

    async def work():
        nonlocal created

        save_record(root / "sandbox-claim.json", {"owner": owner, "state": "creation_uncertain"})
        sandbox = await asyncio.to_thread(
            provider.create,
            CreateSandboxFromImageParams(
                name=owner,
                image="python:3.13.13-slim-bookworm",
                language="python",
                os_user="root",
                resources=Resources(cpu=4, memory=8, disk=10),
                labels={"repo2rlenv.job": owner},
                network_block_all=True,
                auto_stop_interval=10,
                auto_delete_interval=0,
                ephemeral=True,
            ),
            timeout=120,
        )
        created = True
        await asyncio.to_thread(sandbox.refresh_data, request_timeout=15)
        resources = {key: getattr(sandbox, key) for key in ("cpu", "memory", "disk")}
        save_record(
            root / "sandbox-claim.json",
            {"owner": owner, "id": sandbox.id, "state": "created", "resources": resources},
        )
        if resources != {"cpu": 4, "memory": 8, "disk": 10} or not sandbox.network_block_all:
            raise ValueError("Provider did not establish the approved offline CPU profile")
        worker = DaytonaWorker(provider, sandbox)
        initialized = await asyncio.to_thread(
            worker.exec,
            ["mkdir", "-p", "/work", "/work/logs", "/work/probe-counts"],
            timeout=30,
        )
        initialized.checked("Initialize infrastructure-only check")
        async_box = await async_client.get(sandbox.id, request_timeout=15)
        remote = Remote(worker, sandbox, root, work_deadline, 4, session_process=async_box.process)
        for name, expected in [("success", 0), ("nonzero", 7), ("lost-ack", 0)]:
            if name == "lost-ack":
                remote.session_process = LoseAcknowledgement(
                    async_box.process, root / "injected-loss.json", work_deadline
                )
            started = time.time()
            observed = await remote.command(["python", "-c", program(name, expected)], 20, name)
            if (
                observed["exit_code"] != expected
                or observed["timed_out"]
                or json.loads(observed["log"]) != {"case": name, "synthetic": True}
            ):
                raise ValueError("Original synthetic command result did not match its contract")
            count_path = root / "execution-counts" / (name + ".txt")
            count_path.parent.mkdir(exist_ok=True)
            await remote.download("/work/probe-counts/" + name + ".txt", count_path)
            count = count_path.read_text().splitlines()
            if count != ["ran"]:
                raise ValueError("Observed execution count is not one")
            operation = json.loads(
                (root / "operations" / f"{remote.operation:04d}" / "operation.json").read_text()
            )
            if name == "lost-ack" and not operation.get("transport_recovery", {}).get(
                "completion_receipt_verified"
            ):
                raise ValueError("Injected loss did not use verified original receipt recovery")
            result["cases"].append(
                {
                    "name": name,
                    "expected_exit_code": expected,
                    "actual_exit_code": observed["exit_code"],
                    "observed_executions": len(count),
                    "controller_elapsed_seconds": time.time() - started,
                    "remote_elapsed_seconds": observed.get("elapsed_seconds"),
                    "nonce_and_log_hash_verified": operation["state"] == "returned",
                }
            )
            save_record(root / "result.json", result)
        result["status"] = "checks_passed_cleanup_pending"

    try:
        async with asyncio.timeout(config["seconds"]):
            await work()
    except BaseException as error:
        primary = error
        result["error_type"] = type(error).__name__
    finally:
        cleanup_deadline = time.time() + config["cleanup_seconds"]
        try:
            async with asyncio.timeout(15):
                await async_client.close()
        except BaseException as error:
            result["client_close_error_type"] = type(error).__name__
            if primary is None:
                primary = error
        try:
            async with asyncio.timeout(max(0, cleanup_deadline - time.time())):
                cleaned = await asyncio.to_thread(cleanup, owner, provider)
            save_record(root / "cleanup.json", cleaned)
            result["cleanup_verified"] = created and cleaned["passed"]
        except BaseException as error:
            result["cleanup_error_type"] = type(error).__name__
            if primary is None:
                primary = error
        result["status"] = (
            "compatibility_observed"
            if primary is None and result["cleanup_verified"] and len(result["cases"]) == 3
            else "incomplete"
        )
        result["finished"] = time.time()
        save_record(root / "result.json", result)
    if primary is not None:
        raise primary
    if not result["cleanup_verified"]:
        raise RuntimeError("Compatibility sandbox cleanup needs reconciliation")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    value = asyncio.run(run(json.loads(args.config.read_text()), args.root))
    print(json.dumps(value))
