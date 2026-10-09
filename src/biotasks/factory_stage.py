"""Prepare reproducible worker specifications without seed-specific instructions."""

import argparse
import hashlib
import json
from pathlib import Path

from biotasks.prompts import load_prompt

STAGE_PROMPTS = {
    "authoring": "notebook-task-v1",
    "review": "notebook-review-v1",
    "repair": "notebook-repair-v1",
}


def stage_spec(stage: str, archive: Path, request_cap: int, wall_seconds: int) -> dict:
    """Bind a worker invocation to a packaged prompt and immutable input bytes.

    Campaign accounting must reserve a session before submitting this spec. This
    helper neither authorizes execution nor grants extra repair/review sessions.
    """
    if stage not in STAGE_PROMPTS:
        raise ValueError("Unknown factory stage")
    if not 1 <= request_cap <= 40 or not 1 <= wall_seconds <= 1200:
        raise ValueError("Stage exceeds campaign session limits")
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    name = STAGE_PROMPTS[stage]
    prompt = load_prompt(name)
    return {
        "schema_version": 1,
        "stage": stage,
        "model": "glm-5.3",
        "request_cap": request_cap,
        "output_cap": 16384,
        "wall_seconds": wall_seconds,
        "input_zip_sha256": digest.hexdigest(),
        "prompt_name": name,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt": prompt,
        "development_mode": "factory_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGE_PROMPTS, required=True)
    parser.add_argument("--input-zip", type=Path, required=True)
    parser.add_argument("--request-cap", type=int, required=True)
    parser.add_argument("--wall-seconds", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = stage_spec(args.stage, args.input_zip, args.request_cap, args.wall_seconds)
    with args.output.open("x") as destination:
        destination.write(json.dumps(spec, indent=2) + "\n")


if __name__ == "__main__":
    main()
