"""Retain only this run's sandboxes until its exported evidence is verified."""

import json
import os
import shlex
from pathlib import Path

from harbor.environments.daytona import DaytonaEnvironment


class RetainedDaytona(DaytonaEnvironment):
    async def start(self, force_build):
        try:
            await super().start(force_build)
        finally:
            if self._sandbox is not None:
                path = Path(os.environ["BIOTASKS_OWNED_SANDBOXES"])
                with path.open("a") as out:
                    out.write(json.dumps({"id": self._sandbox.id}) + "\n")

    async def stop(self, delete):
        if self._sandbox is not None:
            record = {
                "id": self._sandbox.id,
                "requested_cpu": self._effective_cpus,
                "requested_memory_mb": self._effective_memory_mb,
                "requested_storage_mb": self._effective_storage_mb,
            }
            script = """import json,os
from pathlib import Path
names=['cpu.max','cpu.stat','memory.max','memory.peak','memory.events']
result={n:(Path('/sys/fs/cgroup')/n).read_text().strip() for n in names if (Path('/sys/fs/cgroup')/n).exists()}
s=os.statvfs('/')
result['filesystem_total_bytes']=s.f_blocks*s.f_frsize
result['filesystem_available_bytes']=s.f_bavail*s.f_frsize
print(json.dumps(result))
"""
            try:
                result = await self.exec(
                    command="python3 -c " + shlex.quote(script), timeout_sec=10
                )
                record["measurements"] = (
                    json.loads(result.stdout) if not result.return_code else None
                )
                record["probe_exit_code"] = result.return_code
            except Exception as error:
                record["probe_error_type"] = type(error).__name__
            with (
                Path(os.environ["BIOTASKS_OWNED_SANDBOXES"])
                .with_name("sandbox-resources.jsonl")
                .open("a") as out
            ):
                out.write(json.dumps(record) + "\n")
        # Direct single-container mode only. The campaign rejects compose tasks.
        await super().stop(delete=False)
