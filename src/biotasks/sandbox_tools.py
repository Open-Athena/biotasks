"""Transport Pi's file and shell operations to an existing task environment.

No model-provided command or path is executed/opened on the orchestrator host.
The environment owns user, network and resource enforcement.
"""

import asyncio
import base64
import json
import math
import shlex
import time
from collections.abc import Awaitable, Callable

FILE_OPERATION = r"""
import base64,json,os,sys
from pathlib import Path
p=json.loads(base64.b64decode(sys.argv[1]))
path=Path(p['path'])
op=p['operation']
if op=='read':
    with path.open('rb') as f: data=f.read(16*1024*1024+1)
    if len(data)>16*1024*1024: raise ValueError('File exceeds 16 MiB read limit; use shell tools for bounded inspection')
    result={'data':base64.b64encode(data).decode()}
elif op=='access':
    if not os.access(path,os.R_OK): raise PermissionError('File is not readable')
    result={}
elif op=='mkdir':
    path.mkdir(parents=True,exist_ok=True);result={}
elif op=='write':
    path.write_bytes(base64.b64decode(p['data'],validate=True));result={}
else: raise ValueError('Unknown file operation')
print(json.dumps(result))
"""


class SandboxTools:
    """Dispatch bounded operations through an injected environment executor."""

    def __init__(self, execute: Callable[..., Awaitable], deadline: float):
        self.execute = execute
        self.deadline = deadline
        self.records: list[dict] = []
        self._lock = asyncio.Lock()

    async def dispatch(self, payload: dict) -> dict:
        # One operation at a time: preserve ordering and the experiment's concurrency limit.
        async with self._lock:
            remaining = self.deadline - time.monotonic()
            if remaining <= 1:
                raise TimeoutError("Solver deadline expired")
            operation = payload.get("operation")
            if operation not in {"read", "access", "mkdir", "write", "bash"}:
                raise ValueError("Unknown sandbox operation")
            # Reserve one second for timeout(1)'s forced process-group cleanup.
            timeout = min(remaining - 1, 120.0)
            if operation == "bash":
                command, cwd = payload.get("command"), payload.get("cwd")
                if not isinstance(command, str) or not isinstance(cwd, str):
                    raise ValueError("Shell command and cwd must be strings")
                requested = payload.get("timeout", 120)
                if not isinstance(requested, (int, float)) or not math.isfinite(requested):
                    raise ValueError("Invalid shell timeout")
                timeout = min(timeout, max(0.1, requested))
                command = (
                    f"cd {shlex.quote(cwd)} && "
                    f"timeout --kill-after=1s {timeout:.3f}s bash -lc {shlex.quote(command)}"
                )
            else:
                if not isinstance(payload.get("path"), str):
                    raise ValueError("File path must be a string")
                if operation == "write":
                    if not isinstance(payload.get("data"), str):
                        raise ValueError("Write data must be base64 text")
                    base64.b64decode(payload["data"], validate=True)
                encoded = base64.b64encode(json.dumps(payload).encode()).decode()
                if len(encoded) > 100_000:
                    raise ValueError(
                        "File operation exceeds transport limit; write in smaller chunks"
                    )
                command = f"python3 -c {shlex.quote(FILE_OPERATION)} {shlex.quote(encoded)}"
            start = time.monotonic()
            record = {"operation": operation, "status": "running", "timeout_seconds": timeout}
            self.records.append(record)
            try:
                result = await asyncio.wait_for(
                    self.execute(command=command, timeout_sec=max(1, math.ceil(timeout))),
                    timeout=remaining,
                )
                record.update(status="completed", exit_code=result.return_code)
                if operation == "bash":
                    return {
                        "exitCode": result.return_code,
                        "stdout": result.stdout or "",
                        "stderr": result.stderr or "",
                    }
                if result.return_code:
                    raise RuntimeError((result.stderr or "Sandbox file operation failed")[-4096:])
                return json.loads(result.stdout)
            except BaseException as error:
                record.update(status="failed", error_type=type(error).__name__)
                raise
            finally:
                record["elapsed_seconds"] = round(time.monotonic() - start, 3)
