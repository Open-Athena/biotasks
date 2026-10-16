"""Restore hash-verified task data for native Harbor packaging on the Iris host."""

import json
import os
import shutil
import sys
from pathlib import Path

from coverage_inputs import restore
from materialization_inputs import archive_selection


def main(config_path):
    import fsspec

    config = json.loads(Path(config_path).read_text())
    if config["entrypoint"] != "run_scientific_native.py":
        raise ValueError("Native task entrypoint required")
    prior = Path(__file__).parent / config["materialization_directory"]
    destination = Path("/evidence/native/materialized")
    shutil.copytree(prior, destination)
    items = archive_selection(prior)
    receipts = restore(
        items,
        prefix=os.environ["BIOTASKS_REFERENCE_ARCHIVE"].rstrip("/"),
        root=Path("/work/native-inputs"),
        open_source=lambda uri: fsspec.open(uri, "rb").open(),
        byte_limit=sum(p["bytes"] for p in items),
    )
    for kind in ("inputs", "reference", "oracle_outputs"):
        shutil.copytree(Path("/work/native-inputs/grading/materialized") / kind, destination / kind)
    Path("/evidence/native/retrieval.json").write_text(json.dumps(receipts, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
