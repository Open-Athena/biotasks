"""Restore exact archived terminal outputs with the existing streaming retriever."""

import json
import os
import sys
from pathlib import Path

from coverage_inputs import restore

HERE = Path(__file__).parent


def selected_outputs(config):
    if config.get("materialization_directory"):
        from materialization_inputs import archive_selection

        return archive_selection(
            HERE / config["materialization_directory"]
        ), "grading/materialized/reference/"
    snapshot = json.loads(
        (HERE / config["reference_directory"] / "artifact-manifest.json").read_text()
    )
    replay = HERE / config["replay_directory"]
    manifest = json.loads((replay / "artifact-manifest.json").read_text())
    result = json.loads((replay / "result.json").read_text())
    if not result["all_outputs_byte_identical_to_original"] or not result["cleanup_verified"]:
        raise ValueError("Successful reference replay evidence required")
    by_name = {p["path"]: p for p in snapshot["large_outputs"]}
    prefix = "reference-replay/replay/trials/1/outputs/"
    selected = [p for p in manifest["large_outputs"] if p["path"].startswith(prefix)]
    if {p["path"].removeprefix(prefix) for p in selected} != set(by_name):
        raise ValueError("Archived replay outputs differ from the frozen inventory")
    for p in selected:
        expected = by_name[p["path"].removeprefix(prefix)]
        if (p["bytes"], p["sha256"]) != (expected["bytes"], expected["sha256"]):
            raise ValueError("Replay and original output identities disagree")
    return selected, prefix


def main(config_path):
    import fsspec

    config = json.loads(Path(config_path).read_text())
    if config["entrypoint"] != "run_notebook_grader.py":
        raise ValueError("Wrong entrypoint for grading input restoration")
    selected, prefix = selected_outputs(config)
    root = Path("/work/grading-inputs")
    root.mkdir(exist_ok=False)
    receipts = restore(
        selected,
        prefix=os.environ["BIOTASKS_REFERENCE_ARCHIVE"].rstrip("/"),
        root=root,
        open_source=lambda uri: fsspec.open(uri, "rb").open(),
        byte_limit=sum(p["bytes"] for p in selected),
    )
    # Exact recorded size is a transport-integrity check, not a model context cap.
    evidence = Path("/evidence/grading-retrieval")
    evidence.mkdir(exist_ok=False)
    (evidence / "receipt.json").write_text(
        json.dumps(
            {"files": receipts, "original_hashes_verified": True, "relative_output_root": prefix},
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main(sys.argv[1])
