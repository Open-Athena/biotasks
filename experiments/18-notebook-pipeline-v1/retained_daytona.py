"""Retain only this run's sandboxes until its exported evidence is verified."""

import json
import os
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
        # Direct single-container mode only. The campaign rejects compose tasks.
        await super().stop(delete=False)
