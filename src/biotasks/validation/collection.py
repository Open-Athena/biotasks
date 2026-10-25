"""Classify original controls from source-bound native artifacts, not job status."""

import json
import subprocess
from pathlib import Path
from typing import Any

from biotasks.validation.archives import records, verify_package
from biotasks.validation.files import MAX_ARCHIVE, require, safe, sha
from biotasks.validation.planning import TOOLS
from biotasks.validation.recipes import tagged_recipe


def download(account: dict[str, Any], directory: Path, gcloud: str) -> Path:
    output = account["output_archive"]
    require(output["state"] == "uploaded", "No uploaded execution archive")
    require(0 < output["size_bytes"] <= MAX_ARCHIVE, "Execution archive size bound")
    run = account["job_id"].removeprefix("/exedev/")
    require(
        output["uri"].startswith("gs://") and "/task-outputs/exedev/" + run + "/" in output["uri"],
        "Output namespace changed",
    )
    target = directory / "runtime.tar.zst"
    if not target.exists():
        temporary = directory / "download.partial"
        temporary.unlink(missing_ok=True)
        try:
            subprocess.run(
                [gcloud, "storage", "cp", "--quiet", output["uri"], str(temporary)],
                check=True,
                capture_output=True,
                timeout=180,
            )
            require(
                temporary.stat().st_size == output["size_bytes"]
                and sha(temporary) == output["sha256"],
                "Downloaded output differs",
            )
            temporary.rename(target)
        finally:
            temporary.unlink(missing_ok=True)
    require(
        target.stat().st_size == output["size_bytes"] and sha(target) == output["sha256"],
        "Stored output differs",
    )
    return target


def envelope(
    raw: Path, submission: dict[str, Any], payload: dict[str, str], operation: str, primary: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    outer = records(raw, "tar.zst")
    require("result.json" in outer, "Missing final source-bound report; retain remote data")
    report = json.loads(outer["result.json"]["data"])
    expected = {n: v for n, v in payload.items() if n != "payload.json"}
    require(
        report.get("run_id") == primary and report.get("operation") == operation,
        "Report identity changed",
    )
    require(
        report.get("worker_id") == submission["worker_id"]
        and report.get("payload_sha256") == expected,
        "Execution source/worker changed",
    )
    require(
        report.get("configuration_verified") is True
        and isinstance(report.get("finished"), (int, float)),
        "Incomplete report",
    )
    output = report["output_sha256"]
    require(set(output) == set(outer) - {"result.json", "work-state.json"}, "Unrecorded output")
    for name, digest in output.items():
        require(outer[safe(name)]["sha256"] == digest, "Output hash changed")
    return report, outer


def parse_control(
    control: dict[str, Any], task: dict[str, Any], packed: dict[str, Any]
) -> dict[str, Any]:
    require(
        control["task"] == task["task"] and control["agent"] in ("nop", "oracle"), "Unknown control"
    )
    require(
        control["verifier_timeout_seconds"] == task["verifier_seconds"], "Verifier deadline changed"
    )
    trials = control.get("trial_results", [])
    require(len(trials) <= 1, "Unexpected additional trial")
    trial = trials[0]["result"] if trials else {}
    for item in trials:
        require(
            json.loads(packed["jobs/" + safe(item["path"])]["data"]) == item["result"],
            "Trial summary differs from native bytes",
        )
    for name, text in control.get("reward_files", {}).items():
        require(
            packed["jobs/" + safe(name)]["data"].decode() == text,
            "Reward summary differs from native bytes",
        )
    details = [
        json.loads(text)
        for name, text in control.get("reward_files", {}).items()
        if name.endswith("/reward-details.json")
    ]
    require(len(details) <= 1, "Unexpected additional reward")
    detail = details[0] if details else {}
    reward = ((trial.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    if details:
        require(reward == detail["reward"], "Native reward disagreement")
    logs = [
        {"path": n, "bytes": r["bytes"], "sha256": r["sha256"]}
        for n, r in packed.items()
        if n.startswith("jobs/" + control["name"] + "/") and n.endswith("/verifier/test-stdout.txt")
    ]
    require(len(logs) <= 1, "Unexpected additional verifier log")
    return {
        "agent": control["agent"],
        "state": control["state"],
        "wrapper_exit": control.get("exit_code"),
        "trial_present": bool(trial),
        "reward_details_present": bool(details),
        "exception": trial.get("exception_info"),
        "native_reward": reward,
        "raw_test_logs": logs,
        **{
            k: detail.get(k)
            for k in (
                "parse_status",
                "resolved",
                "command_resolved",
                "exit_code",
                "f2p_passed",
                "f2p_total",
                "p2p_passed",
                "p2p_total",
                "untracked_failed_count",
            )
        },
    }


def pair_flags(rows: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, bool]:
    sides = {r["agent"]: r for r in rows}
    require(len(sides) == len(rows), "Duplicate control side")
    complete = set(sides) == {"nop", "oracle"} and all(
        r["state"] == "completed"
        and r["wrapper_exit"] == 0
        and r["trial_present"]
        and r["reward_details_present"]
        and not r["exception"]
        and r["parse_status"] == "ok"
        and r["f2p_total"] == task["expected_f2p"]
        and r["p2p_total"] == task["expected_p2p"]
        and len(r["raw_test_logs"]) == 1
        for r in sides.values()
    )
    return {
        "complete_parseable_pair": complete,
        "positive_control_pair": bool(
            complete
            and sides["nop"]["native_reward"] == 0
            and sides["oracle"]["native_reward"] == 1
            and sides["oracle"]["resolved"] is True
        ),
        "clean_oracle_command": bool(
            complete
            and sides["oracle"]["command_resolved"] is True
            and sides["oracle"]["exit_code"] == 0
        ),
        "all_p2p_pass_both": bool(
            complete and all(r["p2p_passed"] == r["p2p_total"] for r in sides.values())
        ),
    }


def classify(
    group: dict[str, Any], report: dict[str, Any], outer: dict[str, Any]
) -> dict[str, Any]:
    task = group["task"]
    config = {
        "stage": report["stage"],
        "error": report.get("error"),
        "input_package_verified": False,
        "task_package_verified": False,
    }
    if "input-package.tar.gz" in outer:
        require(
            outer["input-package.tar.gz"]["sha256"] == group["package"]["sha256"],
            "Input package changed",
        )
        verify_package(outer["input-package.tar.gz"]["data"], group["package"]["files"])
        config["input_package_verified"] = True
    packed = {}
    if "control-artifacts.tar.gz" in outer:
        packed = records(outer["control-artifacts.tar.gz"]["data"], "tar.gz")
        expected = {r["path"]: r for r in task["files"]}
        require(
            {n for n in packed if n.startswith("outputs/")} == set(expected), "Task members changed"
        )
        for name, item in expected.items():
            require(
                packed[name]["sha256"] == item["sha256"]
                and packed[name]["mode"] == int(item["mode"], 8),
                "Task bytes or modes changed",
            )
        config["task_package_verified"] = True
    builds = [
        json.loads(line)
        for line in outer.get("bounded-builds.jsonl", {"data": b""})["data"].decode().splitlines()
    ]
    identities = [
        json.loads(line)
        for line in outer.get("image-identities.jsonl", {"data": b""})["data"].decode().splitlines()
    ]
    for build in builds:
        if build.get("cached") or build.get("blocked_by_prior_build_failure"):
            continue
        raw = (
            group["prefix"].encode()
            if build["kind"] == "bootstrap"
            else packed[task["relative_directory"] + "/environment/Dockerfile"]["data"]
        )
        recipe = tagged_recipe(raw, group["run_id"])
        require(
            packed["infra/" + build["dockerfile_sha256"] + ".Dockerfile"]["data"] == recipe,
            "Execution recipe changed beyond owner label",
        )
    controls = (
        json.loads(outer["controls/controls.json"]["data"])
        if "controls/controls.json" in outer
        else []
    )
    rows = [parse_control(c, task, packed) for c in controls]
    flags = pair_flags(rows, task)
    for identity in identities:
        require(
            identity["task"] == task["task"] and identity["git_head"] == task["base_commit"],
            "Wrong task checkout",
        )
        latest = [
            b
            for b in builds
            if b["kind"] == "task"
            and b.get("exit_code") == 0
            and b["finished"] < identity["captured"]
        ]
        require(
            bool(latest) and latest[-1]["image_id"] == identity["image_id"],
            "Unbound execution image",
        )
    if flags["complete_parseable_pair"]:
        unchanged = json.loads(outer["controls/task-files-unchanged.json"]["data"])
        expected_hashes = {r["path"]: r["sha256"] for r in task["files"]}
        require(
            unchanged["verified"] and unchanged["before"] == unchanged["after"] == expected_hashes,
            "Grading assets changed",
        )
        require(
            len(identities) == 2
            and config["task_package_verified"]
            and config["input_package_verified"],
            "Incomplete source provenance",
        )
        native = json.loads(outer["native-source-parity.json"]["data"])
        require(
            all(
                native[n]["verified"] and native[n]["wheel_sha256"] == TOOLS[n + "_wheel_sha256"]
                for n in ("harbor", "tenacity")
            ),
            "Native wheel source parity missing",
        )
    no_creation = report.get("cleanup", {}).get("verified_no_creation") is True
    if no_creation:
        require(
            report.get("creation_started") is False and report.get("controls_started") is False,
            "Contradictory no-creation proof",
        )
    return {
        **config,
        "controls": rows,
        **flags,
        "verified_no_creation": no_creation,
        "control_archive_sha256": outer.get("control-artifacts.tar.gz", {}).get("sha256"),
        "protected_base": report.get("protected_base"),
        "verified_stopped": report.get("stop", {}).get("verified_stopped", no_creation),
        "model_calls": 0,
        "task_repairs": 0,
    }
