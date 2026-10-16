"""Launch only artifact-grader construction/controls in the existing sandbox runner."""

import asyncio
import json
import os
from pathlib import Path

from run_reference_setup import run

if __name__ == "__main__":
    config = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    if config["entrypoint"] != "run_notebook_grader.py":
        raise ValueError("Grading entrypoint cannot launch another stage")
    asyncio.run(
        run(
            config,
            root=Path("/evidence/grading"),
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
        )
    )
