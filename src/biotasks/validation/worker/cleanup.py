"""Remove only one run's Docker resources, leaves first; never rerun generation."""

import json
import subprocess

from biotasks.validation.files import require


def cleanup(binary, run, protected=None):
    records = []

    def command(*args):
        return subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=90)

    def listing(*args):
        result = command(*args)
        result.check_returncode()
        return sorted(set(result.stdout.split()))

    before = None
    if protected:
        require(protected["run_id"] == run, "Worker contract failed at worker/cleanup.py:20")
        raw = command("image", "inspect", protected["ref"])
        if raw.returncode == 0:
            before = json.loads(raw.stdout)[0]["Id"]
            require(
                before == protected["image_id"], "Worker contract failed at worker/cleanup.py:24"
            )
        else:
            require("No such image" in raw.stderr, "Worker contract failed at worker/cleanup.py:26")
    for label in ["biotasks.run=", "biotasks.controller="]:
        ids = listing("ps", "-aq", "--filter", "label=" + label + run)
        if ids:
            command("rm", "-f", *ids).check_returncode()
    # Earlier deletions can also remove ancestors; refresh before each pass.
    for attempt in range(32):
        ids = listing("image", "ls", "-aq", "--no-trunc", "--filter", "label=biotasks.run=" + run)
        if not ids:
            break
        removed = False
        for image in ids:
            result = command("image", "rm", "--no-prune", "-f", image)
            records.append({"pass": attempt, "image": image, "exit_code": result.returncode})
            removed |= result.returncode == 0
        if not removed:
            break
    volumes = listing("volume", "ls", "-q", "--filter", "label=biotasks.run=" + run)
    for volume in volumes:
        command("volume", "rm", volume).check_returncode()
    remaining = {
        "containers": listing("ps", "-aq", "--filter", "label=biotasks.run=" + run),
        "controllers": listing("ps", "-aq", "--filter", "label=biotasks.controller=" + run),
        "images": listing(
            "image", "ls", "-aq", "--no-trunc", "--filter", "label=biotasks.run=" + run
        ),
        "volumes": listing("volume", "ls", "-q", "--filter", "label=biotasks.run=" + run),
    }
    result = {
        "run_id": run,
        "removal_attempts": records,
        "remaining": remaining,
        "verified_empty": not any(remaining.values()),
    }
    if protected:
        raw = command("image", "inspect", protected["ref"])
        after = json.loads(raw.stdout)[0]["Id"] if raw.returncode == 0 else None
        if before:
            require(after == before, "Shared public parent image was not preserved")
        result["protected_public_base"] = dict(
            ref=protected["ref"],
            present_before=before is not None,
            image_id_after=after,
            preserved=bool(before and after == before),
        )
    return result
