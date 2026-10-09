"""Prepare reproducible worker specifications without seed-specific instructions."""

import argparse
import hashlib
import json
from pathlib import Path

from biotasks.prompts import load_prompt

STAGE_PROMPTS = {
    "authoring": "notebook-task-v1",
    "specification": "notebook-specification-v1",
    "construction": "notebook-construction-v1",
    "review": "notebook-review-v1",
    "repair": "notebook-repair-v1",
}
WORKFLOWS = {
    1: ("authoring", "review", "repair", "review_after_repair"),
    2: ("specification", "construction", "review", "repair", "review_after_repair"),
}
STAGE_ROLES = {name: name for name in STAGE_PROMPTS} | {"review_after_repair": "review"}


def predecessor_slot(slot: str, workflow_version: int) -> str | None:
    if workflow_version not in WORKFLOWS or slot not in WORKFLOWS[workflow_version]:
        raise ValueError("Unknown stage in the fixed workflow")
    sequence = WORKFLOWS[workflow_version]
    index = sequence.index(slot)
    return sequence[index - 1] if index else None


def worker_template(
    stage: str, request_cap: int, wall_seconds: int, limits: dict | None = None
) -> dict:
    """Declare finite per-stage limits; default bounds preserve the first batch."""
    if stage not in STAGE_PROMPTS:
        raise ValueError("Unknown factory stage")
    limits = (
        limits
        if limits is not None
        else {"request_cap": 40, "wall_seconds": 1200, "output_cap": 16384}
    )
    if set(limits) != {"request_cap", "wall_seconds", "output_cap"} or any(
        type(value) is not int or value < 1 for value in limits.values()
    ):
        raise ValueError("Explicit positive stage limits required")
    if limits["request_cap"] > 60 or limits["wall_seconds"] > 1200 or limits["output_cap"] > 16384:
        raise ValueError("Stage limits exceed worker enforcement ceilings")
    if (
        type(request_cap) is not int
        or type(wall_seconds) is not int
        or not 1 <= request_cap <= limits["request_cap"]
        or not 1 <= wall_seconds <= limits["wall_seconds"]
    ):
        raise ValueError("Stage exceeds campaign session limits")
    name = STAGE_PROMPTS[stage]
    prompt = load_prompt(name)
    return {
        "schema_version": 1,
        "stage": stage,
        "model": "glm-5.3",
        "request_cap": request_cap,
        "output_cap": limits["output_cap"],
        "wall_seconds": wall_seconds,
        "prompt_name": name,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt": prompt,
        "development_mode": "factory_only",
    }


def stage_spec(
    stage: str, archive: Path, request_cap: int, wall_seconds: int, limits: dict | None = None
) -> dict:
    """Bind a worker invocation to a packaged prompt and immutable input bytes.

    Campaign accounting must reserve a session before submitting this spec. This
    helper neither authorizes execution nor grants extra repair/review sessions.
    """
    template = worker_template(stage, request_cap, wall_seconds, limits)
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return template | {"input_zip_sha256": digest.hexdigest()}


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
