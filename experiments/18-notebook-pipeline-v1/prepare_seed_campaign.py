"""Freeze fresh full-panel inputs and a bounded whole-seed execution plan."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from biotasks.factory_batch import execution_limits, freeze_batch
from biotasks.factory_inputs import assemble
from biotasks.prompts import load_prompt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-input-manifest", type=Path, required=True)
    parser.add_argument("--previous-archives", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    previous = json.loads(args.previous_input_manifest.read_text())
    protocol = json.loads(args.protocol.read_text())
    budget = json.loads(args.budget.read_text())
    shared = {
        "protocol.json": args.protocol.read_bytes(),
        "prompt.md": load_prompt("notebook-task-v1").encode(),
        "review-prompt.md": load_prompt("notebook-review-v1").encode(),
        "repair-prompt.md": load_prompt("notebook-repair-v1").encode(),
    }
    args.archives.mkdir(exist_ok=False)
    rows, inputs = [], {}
    for row in previous["inputs"]:
        seed = row["seed"]
        source = args.previous_archives / (seed + ".zip")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError("Previous source input archive changed")
        selected = [name for name in row["members"] if name not in shared]
        target = args.archives / (seed + ".zip")
        result = assemble(source, selected, shared, target)
        rows.append({"seed": seed, "source_archive_sha256": digest, **result})
        inputs[seed] = target
    first = budget["stage_limits"]["specification"]
    receipt = freeze_batch(
        revision,
        inputs,
        protocol,
        first["request_cap"],
        first["wall_seconds"],
        budget["concurrency"],
        args.batch,
        execution_budget=args.budget,
        workflow_version=2,
        stage_limits=budget["stage_limits"],
        seed_execution=budget["seed_execution"],
    )
    execution_limits(json.loads(args.batch.read_text()), args.budget.read_bytes())
    args.manifest.write_text(
        json.dumps(
            {
                "status": "prepared_not_submitted",
                "inputs": rows,
                "batch": receipt,
                "factory_revision": revision,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
