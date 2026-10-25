"""One documented async session submission; observations never resubmit a command.

This transport is opt-in until compatibility is measured. The caller still owns
the sandbox and verifies its nonce-bound command receipt and original log hash.
"""

import asyncio
import hashlib
import inspect
import shlex
import time
import uuid
from contextlib import asynccontextmanager

from daytona import AsyncDaytona, SessionExecuteRequest
from repo2rlenv.execution.base import CommandResult
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.execution.read_retry import transient_connection_error


async def session_command(process, argv, *, timeout, directory):
    """Use AsyncProcess, including its cancellable WebSocket connection setup."""
    if not argv or type(timeout) is not int or timeout <= 0:
        raise ValueError("Session execution needs argv and a positive timeout")
    if not inspect.iscoroutinefunction(process.create_session):
        raise TypeError("Session transport requires the asynchronous Daytona SDK")
    deadline = time.monotonic() + timeout
    session = "biotasks-" + uuid.uuid4().hex
    command = shlex.join(argv)
    record = {
        "session_id": session,
        "state": "creating",
        "timeout_seconds": timeout,
        "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
        "submission_attempts": 0,
        "creation_attempts": 0,
        "command_reexecuted": False,
        "started": time.time(),
    }
    path = directory / "session-transport.json"
    save_record(path, record)

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError("Session observation exhausted its original allowance")
        return value

    async def rpc(method, *args, **kwargs):
        async with asyncio.timeout(remaining()):
            return await method(*args, **kwargs)

    async def status():
        observed = await rpc(
            process.get_session_command,
            session,
            record["command_id"],
            request_timeout=min(30, remaining()),
        )
        if observed.id != record["command_id"] or observed.command != command:
            raise ValueError("Session status differs from the submitted command identity")
        return observed

    def append(name, chunk):
        if not isinstance(chunk, str):
            raise ValueError("Session log callback did not supply text")
        with (directory / name).open("a", encoding="utf-8", newline="") as output:
            output.write(chunk)

    async def stdout(chunk):
        await asyncio.to_thread(append, "session-stream-stdout.txt", chunk)

    async def stderr(chunk):
        await asyncio.to_thread(append, "session-stream-stderr.txt", chunk)

    completed = False
    try:
        for creation in range(2):
            record["creation_attempts"] += 1
            save_record(path, record)
            try:
                await rpc(process.create_session, session, request_timeout=min(30, remaining()))
                if creation:
                    record["creation_recovery"] = "created_after_confirmed_absence"
                break
            except Exception as error:
                # No execute request has been made. Resolve this same session;
                # never turn an uncertain command into a second submission.
                if not transient_connection_error(error) or not inspect.iscoroutinefunction(
                    getattr(process, "get_session", None)
                ):
                    raise
                observation = {"attempt": creation + 1, "error_type": type(error).__name__}
                record.setdefault("creation_reconciliation", []).append(observation)
                save_record(path, record)
                try:
                    existing = await rpc(
                        process.get_session, session, request_timeout=min(30, remaining())
                    )
                except Exception as lookup_error:
                    observation["lookup_error_type"] = type(lookup_error).__name__
                    save_record(path, record)
                    if type(lookup_error).__name__ == "DaytonaNotFoundError" and creation == 0:
                        observation["state"] = "confirmed_absent"
                        save_record(path, record)
                        continue
                    raise error from None
                if existing.session_id != session or existing.commands != []:
                    raise ValueError("Creation recovery requires the same empty session") from None
                observation["state"] = "same_empty_session_verified"
                record["creation_recovery"] = "existing_empty_session"
                save_record(path, record)
                break
        # The installed SDK adds5seconds to the execute call's HTTP timeout.
        # Keep that inside this existing transport allowance, not extra runtime.
        submission_timeout = min(30, int(remaining()) - 5)
        if submission_timeout < 1:
            raise TimeoutError("No time remains for a single session submission")
        record.update(state="submitting", submission_attempts=1)
        save_record(path, record)
        response = await rpc(
            process.execute_session_command,
            session,
            SessionExecuteRequest(command=command, run_async=True, suppress_input_echo=True),
            timeout=submission_timeout,
        )
        if not isinstance(response.cmd_id, str) or not response.cmd_id:
            raise ValueError("Session submission did not return a command identity")
        record.update(command_id=response.cmd_id, state="observing")
        save_record(path, record)
        observed = await status()
        stream_error = None
        if observed.exit_code is None:
            try:
                async with asyncio.timeout(remaining()):
                    await process.get_session_command_logs_async(
                        session, response.cmd_id, stdout, stderr
                    )
            except Exception as error:
                stream_error = error
                record["stream_error_type"] = type(error).__name__
                save_record(path, record)
            # A stream ending is not completion evidence. Read the same command
            # once; no polling loop, second submission or sync-exec fallback.
            observed = await status()
        if type(observed.exit_code) is not int:
            if stream_error is not None:
                raise stream_error
            raise RuntimeError("Session closed without a completed command")
        completed = True
        record.update(state="completed", exit_code=observed.exit_code)
        save_record(path, record)
        logs = await rpc(
            process.get_session_command_logs,
            session,
            response.cmd_id,
            request_timeout=min(30, remaining()),
        )
        if any(
            value is not None and not isinstance(value, str)
            for value in (logs.stdout, logs.stderr, logs.output)
        ):
            raise ValueError("Session completion logs did not supply text")
        out, err = logs.stdout or "", logs.stderr or ""
        if not out and not err and logs.output:
            out = logs.output
            record["combined_output_fallback"] = True
        return CommandResult(observed.exit_code, out, err)
    except BaseException as error:
        record.update(state="observation_failed", error_type=type(error).__name__)
        raise
    finally:
        # Clean only a known-completed session. Uncertain commands stay with the
        # owner for receipt reconciliation and sandbox deletion, never retry.
        record["session_cleanup"] = "owner_required"
        if completed and deadline - time.monotonic() >= 1:
            try:
                await rpc(
                    process.delete_session,
                    session,
                    request_timeout=min(5, remaining()),
                )
                record["session_cleanup"] = "deleted"
            except Exception as error:
                record["session_cleanup_error_type"] = type(error).__name__
        record["finished"] = time.time()
        save_record(path, record)


@asynccontextmanager
async def owned_session_process(sandbox_id, root, deadline, *, enabled):
    """Own one async SDK client per stage, including setup or command failures.

    The legacy transport needs no extra client. Session lookup is read-only;
    this context never creates a sandbox or retries a submitted command.
    Closing consumes the existing cleanup allowance, never extends it.
    """
    if not enabled:
        yield None
        return
    client = AsyncDaytona()
    primary = None
    record = {"transport": "async_session", "state": "opening", "started": time.time()}
    path = root / "session-client.json"
    save_record(path, record)
    try:
        async with asyncio.timeout(max(0, min(15, deadline - time.time()))):
            sandbox = await client.get(sandbox_id, request_timeout=15)
        if sandbox.id != sandbox_id:
            raise ValueError("Async client returned a different sandbox identity")
        record["state"] = "open"
        save_record(path, record)
        yield sandbox.process
    except BaseException as error:
        primary = error
        record["primary_error_type"] = type(error).__name__
        raise
    finally:
        try:
            async with asyncio.timeout(15):
                await client.close()
            record["state"] = "closed"
        except BaseException as error:
            record.update(state="close_failed", close_error_type=type(error).__name__)
            if primary is None:
                raise
        finally:
            record["finished"] = time.time()
            save_record(path, record)
