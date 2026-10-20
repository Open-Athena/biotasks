"""Run native history source selection on fixed remaining SWE-Next inputs.

No repository code, install command, tests, author or model is executed here.
Eligible original contexts are retained for their next native stage.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.history.worker import prepare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("BIOTASKS21_TRC_SOURCE_INTAKE") == "1"
    assert not os.environ.get("GLM_BULK_TOKEN") and not os.environ.get("DAYTONA_API_KEY")
    manifest = json.loads((args.inputs / "intake-manifest.json").read_text())
    assert manifest["model_calls"] == manifest["task_specific_fixes"] == 0
    for name, record in manifest["files"].items():
        raw = (args.inputs / name).read_bytes()
        assert len(raw) == record["bytes"]
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for unit in manifest["units"]:
        config = json.loads((args.inputs / unit["config"]).read_text())
        original = json.loads((args.inputs / unit["original_profile"]).read_text())
        expected_options = dict(original["options"], pr_numbers=unit["selected_prs"])
        assert config["repo"] == original["repo"]
        assert config["recipe"] == original["recipe"] == "swe_next"
        assert config["options"] == expected_options
        assert expected_options["target"] == 3 and expected_options["max_candidates"] == 10
        assert [p["number"] for p in config["pulls"]] == unit["selected_prs"]
        started = time.monotonic()
        row = {"unit": unit["unit"], "selected_inputs": len(config["pulls"]), "status": "started"}
        rows.append(row)
        save_record(args.output / "summary.json", {"stage": "native_source_selection_not_build_author_export", "model_calls": 0, "rows": rows})
        try:
            result = prepare(config, args.output / unit["unit"])
            row.update(status="native_selection_completed", attempted=result["attempted"],
                       eligible=len(result["candidates"]), rejected=len(result["rejected"]),
                       candidate_ids=[c["id"] for c in result["candidates"]],
                       repo_revision=result["repo_revision"])
        except Exception as exc:
            row.update(status="native_selection_failed_no_repair", error_type=type(exc).__name__)
            raise
        finally:
            row["elapsed_seconds"] = round(time.monotonic() - started, 3)
            save_record(args.output / "summary.json", {"stage": "native_source_selection_not_build_author_export", "model_calls": 0, "rows": rows})
    print(json.dumps({"model_calls": 0, "rows": rows}), flush=True)


if __name__ == "__main__":
    main()
