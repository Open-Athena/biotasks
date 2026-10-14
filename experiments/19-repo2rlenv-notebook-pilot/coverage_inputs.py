"""Stage immutable prior outputs and run trusted structural inspection on Iris.

This runs in the existing host environment with the storage client. No generated
code executes here, and no analysis matrix is loaded into memory.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from inspect_artifacts import relative_path
from iris_bootstrap import command


def restore(items, *, prefix, root, open_source, byte_limit):
    if sum(item["bytes"] for item in items) > byte_limit:
        raise ValueError("Reference retrieval exceeds byte ceiling")
    receipts = []
    for item in items:
        relative = relative_path(item["path"])
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        count = 0
        with open_source(prefix + "/" + str(relative)) as stream, destination.open("xb") as target:
            while chunk := stream.read(1 << 20):
                count += len(chunk)
                if count > item["bytes"]:
                    raise ValueError("Reference artifact grew beyond its recorded size")
                hasher.update(chunk)
                target.write(chunk)
        if count != item["bytes"] or hasher.hexdigest() != item["sha256"]:
            raise ValueError("Archived reference artifact failed its original hash")
        receipts.append(dict(path=item["path"], bytes=count, sha256=hasher.hexdigest()))
    return receipts


def main(config_path):
    import fsspec

    config = json.loads(Path(config_path).read_text())
    experiment = Path(__file__).parent
    prior = experiment / relative_path(config["reference_run"])
    summary = json.loads((prior / "summary.json").read_text())
    if summary["status"] != "reference_executed" or not summary["durable_archive_download_checked"]:
        raise ValueError("Coverage requires an executed, durably archived reference")
    attempt = "attempt-" + str(summary["successful_attempt"])
    inventory_path = prior / attempt / "artifacts.json"
    inventory = json.loads(inventory_path.read_text())
    manifest = json.loads((prior / "archive-manifest.json").read_text())
    archived = {item["path"]: item for item in manifest["files"]}
    selected = []
    for item in inventory["artifacts"]:
        path = f"reference/{attempt}/outputs/" + str(relative_path(item["path"]))
        original = archived[path]
        if original["sha256"] != item["sha256"] or original["bytes"] != item["bytes"]:
            raise ValueError("Inventory and archive disagree")
        selected.append(dict(path=path, bytes=item["bytes"], sha256=item["sha256"]))
    evidence = Path("/evidence/coverage")
    evidence.mkdir(parents=True, exist_ok=False)
    staging = Path("/work/coverage-inputs")
    staging.mkdir(exist_ok=False)
    started = time.time()
    receipts = restore(
        selected,
        prefix=os.environ["BIOTASKS_REFERENCE_ARCHIVE"].rstrip("/"),
        root=staging,
        open_source=lambda uri: fsspec.open(uri, "rb").open(),
        byte_limit=config["download_ceiling_bytes"],
    )
    (evidence / "retrieval.json").write_text(
        json.dumps(
            dict(files=receipts, hash_verified=True, elapsed_seconds=time.time() - started),
            indent=2,
        )
    )
    deadline = float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"])
    log = evidence / "inspection-setup.log"
    venv = Path("/work/inspection-venv")
    command(
        ["uv", "venv", "--python", sys.executable, str(venv)],
        cwd=experiment,
        deadline=deadline,
        log=log,
    )
    command(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv / "bin/python"),
            "-r",
            str(experiment / "inspection-requirements.txt"),
        ],
        cwd=experiment,
        deadline=deadline,
        log=log,
    )
    command(
        [
            str(venv / "bin/python"),
            str(experiment / "inspect_artifacts.py"),
            str(inventory_path),
            str(staging / "reference" / attempt / "outputs"),
            str(evidence / "profiles"),
        ],
        cwd=experiment,
        deadline=min(deadline, time.time() + config["inspection_seconds"]),
        log=evidence / "inspection.log",
    )
    (evidence / "inspection.json").write_text(
        json.dumps(
            dict(
                completed=True,
                original_hashes_verified_before_and_after=True,
                elapsed_seconds=time.time() - started,
                analysis_rerun=False,
                scientific_validation=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
