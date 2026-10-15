"""Programmatic reference repeats through the existing Daytona lifecycle."""

import asyncio
import json
import os
from pathlib import Path

from run_reference_setup import run

if __name__ == "__main__":
    config = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    if config.get("entrypoint") != "run_reference_replay.py":
        raise ValueError("Replay cannot dispatch a model-driven stage")
    asyncio.run(run(
        config,
        root=Path("/evidence/reference-replay"),
        deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
        endpoint=None, credential=None,
    ))
