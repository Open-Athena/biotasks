"""Summarize original recorded failures without rerunning or repairing inputs."""

import gzip
import json
import re
from pathlib import Path

from biotasks.validation.archives import records
from biotasks.validation.files import read_json, require, sha, write_json

root = Path(__file__).resolve().parent
run = root / "inputs-private/run-001/anndata/runs/generation"
source = run / "generation-source"
readback = read_json(run / "readback.json")
outer = records((run / "runtime.tar.zst").read_bytes(), "tar.zst")
require(readback["durable_readback_verified"] is True, "Original readback not verified")
native_log = outer["native-generation.log"]["data"].decode()
require("'non_bug_pr': 1, 'no_fail_to_pass': 1" in native_log, "Different native filter outcome")
observations = source / "native-observations"


def decoded(name):
    path = observations / name
    with gzip.open(path, "rb") as stream:
        raw = stream.read(2 * 1024**2 + 1)
    require(len(raw) <= 2 * 1024**2, "Recorded observation exceeds diagnostic bound")
    return json.loads(raw), sha(path)


validation, validation_sha = decoded("validation-001-pr-2641.json.gz")
trials = []
for name, phase in (("exec-0015-pr-2641.json.gz", "pre"), ("exec-0016-pr-2641.json.gz", "post")):
    value, digest = decoded(name)
    result, command = value["result"], value["command"]
    out = result["stdout"]
    statuses = [
        line
        for line in out.splitlines()
        if re.match(
            r"tests/test_obsmvarm\.py::test_roundtrips_df_with_different_index\[(?:obs|var)\] (?:FAILED|PASSED)",
            line,
        )
    ]
    module_lines = sorted(
        {
            line
            for line in out.splitlines()
            if "/site-packages/anndata/_core/aligned_mapping.py:" in line
        }
    )
    require(
        len(statuses) == 2 and all("FAILED" in line for line in statuses),
        "Different target outcome",
    )
    require(bool(module_lines), "Package origin not present in original failure")
    summary = next(
        line
        for line in out.splitlines()
        if re.search(r"2 failed, 1536 passed, 578 skipped, 2 xfailed", line)
    )
    trials.append(
        {
            "phase": phase,
            "source_observation": name,
            "sha256": digest,
            "duration_sec": result["duration_sec"],
            "shell_wrapper_exit_code": result["exit_code"],
            "pytest_summary": summary,
            "target_lines": statuses,
            "observed_module_traceback_lines": module_lines,
            "patched_worktree_source": "/workspace/src/anndata/_core/aligned_mapping.py",
            "source_patch_in_command": "diff --git a/src/anndata/_core/aligned_mapping.py"
            in command,
            "source_patch_applied_cleanly": "Applied patch src/anndata/_core/aligned_mapping.py cleanly."
            in result["stderr"],
            "target_index_guard_still_in_failure": "raise ValueError(msg) from None" in out
            and "val.index.equals(self.dim_names)" in out,
        }
    )

(bootstrap_path,) = source.glob("upstream/workspace/bootstrap/**/bootstrap.json")
bootstrap = read_json(bootstrap_path)
require(
    trials[1]["source_patch_in_command"] and trials[1]["source_patch_applied_cleanly"],
    "Head source patch was not applied",
)
require(
    all(row["duration_sec"] < 600 for row in trials),
    "Native validation did not finish within its deadline",
)
summary = {
    "original_run": "/exedev/biotasks53-anndata-001",
    "original_archive_sha256": sha(run / "runtime.tar.zst"),
    "native_exit": readback["native_exit"],
    "native_candidates": 2,
    "native_skipped": {"non_bug_pr": 1, "no_fail_to_pass": 1},
    "validated_pr": 2641,
    "backport_filtered_pr": 2710,
    "exports": len(readback["exported_tasks"]),
    "model_billing": readback["model_billing"],
    "allocated_primary_cpu_hours": read_json(run / "accounting.json")["allocated_cpu_hours"],
    "validation_status": validation["status"],
    "validation_reason": validation["reason"],
    "fail_to_pass_count": len(validation["fail_to_pass"]),
    "pass_to_pass_count": len(validation["pass_to_pass"]),
    "validation_observation_sha256": validation_sha,
    "trials": trials,
    "bootstrap": {
        key: bootstrap[key]
        for key in (
            "iterations",
            "smoke_passed",
            "verify_passed",
            "verify_detail",
            "rebuild_cmds",
            "test_cmds",
        )
    },
    "observed": "Both complete native validations execute the old index guard under site-packages while the head patch changes workspace source; no F2P transition is observed",
    "inference": "The test dependency installation may replace editable anndata0.0.0 with a released dependency; direct_url/realpath/install transaction evidence is needed to prove that exact mechanism",
    "timeout_attribution": "Bootstrap full-suite300s checks time out separately; the changed-file pre/post validations each finish in about206s, so their zero F2P is not a600s validation timeout",
    "scientific_acceptance": False,
    "additional_native_or_model_calls": 0,
    "original_inputs_or_results_modified": False,
}
write_json(root / "recorded-diagnosis.json", summary)
print(
    json.dumps(
        {
            key: summary[key]
            for key in (
                "exports",
                "model_billing",
                "fail_to_pass_count",
                "pass_to_pass_count",
                "observed",
                "inference",
                "additional_native_or_model_calls",
            )
        },
        indent=2,
    )
)
