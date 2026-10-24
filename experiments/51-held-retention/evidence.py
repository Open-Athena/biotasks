"""Independent provenance checks for unaccepted native reward disagreement.

The original collector still raises. These checks cover every control and the
image/wheel/task invariants following that early exception in the old collector.
They never recompute a reward or parse/rewrite native test logs for grading.
"""

import copy
import json
import math
from pathlib import Path

import log_policy
from biotasks.validation import collection, controller
from biotasks.validation.archives import records, verify_package
from biotasks.validation.files import json_sha, read_json, require, safe, sha
from biotasks.validation.planning import TOOLS, UPSTREAM
from biotasks.validation.worker.controls import commands

AUXILIARY = {"cpus": 2, "memory_gib": 4, "disk_gib": 4, "timeout_seconds": 270}
ERROR = "Native reward disagreement"


def reconciled(pipe, role, account):
    run = pipe.group["run_id"] + ("-" + role if role else "")
    ledger = read_json(pipe.ledger)
    entry = next(
        row
        for row in ledger["events"]
        if row.get("kind") == "reserved_cpu_admission" and row.get("run_id") == run
    )
    maximum = pipe.group["resources"]["cleanup_cpu_hours" if role else "maximum_cpu_hours"]
    require(
        entry["state"] == "terminal reconciled"
        and entry["new_paid_capacity"] is False
        and entry["maximum_allocated_cpu_hours"] == maximum,
        "Native CPU admission not source-bound/reconciled",
    )
    require(
        isinstance(account["allocated_cpu_hours"], (int, float))
        and not isinstance(account["allocated_cpu_hours"], bool)
        and math.isfinite(account["allocated_cpu_hours"])
        and 0 <= account["allocated_cpu_hours"] == entry["actual_allocated_cpu_hours"],
        "Native accounting changed",
    )
    return copy.deepcopy(entry)


def accounting(directory, run_id):
    account = read_json(directory / "accounting.json")
    require(
        account["terminal"] is True
        and account["job_id"] == "/exedev/" + run_id
        and isinstance(account["attempts"], int)
        and not isinstance(account["attempts"], bool)
        and account["attempts"] > 0,
        "Missing terminal native accounting",
    )
    require(
        (directory / "runtime.tar.zst").is_file(),
        "Native archive missing locally; retain original data",
    )
    # Existing bytes are checked against uploaded archive size/hash/namespace;
    # this path cannot download or query a job during offline source checking.
    collection.download(account, directory, "forbidden-during-source-verification")
    return account


def auxiliary_contract(pipe, role, **settings):
    """Validate a recorded auxiliary independently, without creating one."""
    original = pipe.group
    directory = pipe.directory / role
    group = read_json(directory / "group.json")
    expected = copy.deepcopy(original)
    expected.update(run_id=original["run_id"] + "-" + role, resources=AUXILIARY)
    reduced = {k: v for k, v in group.items() if k not in ("payload_directory", "payload_sha256")}
    require(
        reduced
        == {k: v for k, v in expected.items() if k not in ("payload_directory", "payload_sha256")},
        "Auxiliary role/group changed",
    )
    payload = directory / "payload"
    require(
        group["payload_directory"] == payload.relative_to(pipe.root).as_posix(),
        "Auxiliary directory changed",
    )
    require(
        set(group["payload_sha256"]) == set(original["payload_sha256"]),
        "Auxiliary member set changed",
    )
    for name, digest in group["payload_sha256"].items():
        path = payload / safe(name)
        require(
            path.is_file() and not path.is_symlink() and sha(path) == digest,
            "Auxiliary payload changed",
        )
        if name not in ("family.json", "payload.json"):
            require(
                digest == original["payload_sha256"][name], "Auxiliary executable/input changed"
            )
    primary = read_json(pipe.directory / "submission.json")
    family = read_json(pipe.root / original["payload_directory"] / "family.json")
    family.update(
        operation=role, resources=AUXILIARY, target_worker_id=primary["worker_id"], **settings
    )
    require(read_json(payload / "family.json") == family, "Auxiliary target/settings changed")
    require(
        read_json(payload / "payload.json")
        == {
            "run_id": original["run_id"],
            "sha256": {k: v for k, v in group["payload_sha256"].items() if k != "payload.json"},
        },
        "Auxiliary source manifest changed",
    )
    return group, directory


def auxiliary(pipe, role, **settings):
    group, directory = auxiliary_contract(pipe, role, **settings)
    primary = read_json(pipe.directory / "submission.json")
    receipt = read_json(directory / "submission.json")
    require(
        receipt["job_id"] == "/exedev/" + group["run_id"]
        and receipt["payload_sha256"] == group["payload_sha256"]
        and receipt["worker_id"] == primary["worker_id"]
        and receipt["worker_tpu_name"] == primary["worker_tpu_name"],
        "Auxiliary worker/submission changed",
    )
    account = accounting(directory, group["run_id"])
    report, _ = collection.envelope(
        directory / "runtime.tar.zst", receipt, group["payload_sha256"], role, pipe.group["run_id"]
    )
    return group, directory, account, report


def controls(task, run_id, family, items, packed):
    require(
        len(items) == 2 and {item["agent"] for item in items} == {"nop", "oracle"},
        "Incomplete native pair provenance",
    )
    output = []
    for item in items:
        command = item["command"]
        require(isinstance(command, list) and command.count("-o") == 1, "Unknown native command")
        jobs = command[command.index("-o") + 1]
        require(
            jobs.endswith("/volumes/" + run_id + "-work/_data/jobs"), "Native job directory differs"
        )
        expected = next(
            row for row in commands(family, Path(jobs)) if row["agent"] == item["agent"]
        )
        require(
            all(
                item[key] == expected[key]
                for key in (
                    "task",
                    "agent",
                    "name",
                    "command",
                    "verifier_timeout_seconds",
                    "wrapper_allowance_seconds",
                )
            ),
            "Native command/deadline/resource changed",
        )
        names, root = log_policy.control_paths(task, item, packed)
        trial = item["trial_results"][0]
        require(
            json.loads(packed["jobs/" + safe(trial["path"])]["data"]) == trial["result"],
            "Native trial summary changed",
        )
        result = trial["result"]
        config = result["config"]
        require(
            result["agent_info"]["name"] == config["agent"]["name"] == item["agent"]
            and config["agent"]["model_name"] is None
            and config["agent"]["import_path"] is None,
            "Native deterministic agent changed",
        )
        require(
            config["task"]["path"] == "/work/" + task["relative_directory"]
            and result["task_id"]["path"] == config["task"]["path"],
            "Native task path changed",
        )
        env = config["environment"]
        require(
            env["type"] == "docker"
            and env["import_path"] is None
            and env["override_cpus"] == 1
            and env["override_memory_mb"] == 6144
            and env["override_gpus"] is None,
            "Native environment override changed",
        )
        require(
            config["verifier_timeout_multiplier"] == 1
            and config["timeout_multiplier"] == 1
            and config["verifier"]["disable"] is False
            and config["verifier"]["override_timeout_sec"] is None,
            "Native trial deadline changed",
        )
        rewards = item.get("reward_files", {})
        for name, text in rewards.items():
            require(
                "jobs/" + safe(name)
                in {root + "verifier/reward-details.json", root + "verifier/reward.txt"}
                and packed["jobs/" + name]["data"].decode() == text,
                "Native reward source binding differs",
            )
        details = [
            json.loads(text)
            for name, text in rewards.items()
            if name.endswith("/reward-details.json")
        ]
        require(len(details) <= 1, "Multiple native detail records")
        native = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        late = details[0].get("reward") if details else None
        require(
            all(
                value is None
                or isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and 0 <= value <= 1
                for value in (native, late)
            ),
            "Unknown native reward representation",
        )
        output.append(
            {
                "agent": item["agent"],
                "trial_path": trial["path"],
                "native_reward": native,
                "recorded_file_reward": late,
                "native_exception": (result.get("exception_info") or {}).get("exception_type"),
                "scientific_acceptance": False,
            }
        )
    return output


def verify(root, task_id):
    plan = controller.verify_plan(root)
    require(plan["repo2rlenv_revision"] == UPSTREAM, "Unsupported native source revision")
    group = next(group for group in plan["tasks"] if group["id"] == task_id)
    pipe = controller.Pipeline(root, plan, group)
    directory = pipe.directory
    held = read_json(directory / "held.json")
    require(
        held["stop_verified"] is True and held["reason"] == ERROR, "Unsupported held-native reason"
    )
    account = accounting(directory, group["run_id"])
    primary = read_json(directory / "submission.json")
    require(
        primary["job_id"] == account["job_id"]
        and primary["payload_sha256"] == group["payload_sha256"],
        "Primary submission changed",
    )
    report, outer = collection.envelope(
        directory / "runtime.tar.zst", primary, group["payload_sha256"], "execute", group["run_id"]
    )
    require(
        report.get("stop", {}).get("verified_stopped") is True,
        "Native execution not verified stopped",
    )
    require(
        outer["input-package.tar.gz"]["sha256"] == group["package"]["sha256"],
        "Native input package changed",
    )
    verify_package(outer["input-package.tar.gz"]["data"], group["package"]["files"])
    try:
        collection.classify(group, report, outer)
    except ValueError as error:
        require(str(error) == ERROR, "Different native provenance/collection error")
    else:
        raise ValueError("Original collector no longer rejects consistency")
    packed = records(outer["control-artifacts.tar.gz"]["data"], "tar.gz")
    native_controls = json.loads(outer["controls/controls.json"]["data"])
    family = read_json(root / group["payload_directory"] / "family.json")
    diagnostics = controls(group["task"], group["run_id"], family, native_controls, packed)
    require(
        any(row["native_reward"] != row["recorded_file_reward"] for row in diagnostics),
        "No native disagreement",
    )
    unchanged = json.loads(outer["controls/task-files-unchanged.json"]["data"])
    expected = {row["path"]: row["sha256"] for row in group["task"]["files"]}
    require(
        unchanged["verified"] is True and unchanged["before"] == unchanged["after"] == expected,
        "Native grading assets changed",
    )
    builds = [
        json.loads(line) for line in outer["bounded-builds.jsonl"]["data"].decode().splitlines()
    ]
    images = [
        json.loads(line) for line in outer["image-identities.jsonl"]["data"].decode().splitlines()
    ]
    require(len(images) == 2, "Native image identities incomplete")
    for image in images:
        require(
            image["task"] == group["task"]["task"]
            and image["git_head"] == group["task"]["base_commit"],
            "Native task checkout differs",
        )
        prior = [
            row
            for row in builds
            if row["kind"] == "task"
            and row.get("exit_code") == 0
            and row["finished"] < image["captured"]
        ]
        require(
            bool(prior) and prior[-1]["image_id"] == image["image_id"],
            "Native image not build-bound",
        )
    native = json.loads(outer["native-source-parity.json"]["data"])
    require(
        all(
            native[name]["verified"] is True
            and native[name]["wheel_sha256"] == TOOLS[name + "_wheel_sha256"]
            for name in ("harbor", "tenacity")
        ),
        "Native wheel parity differs",
    )
    _, stop_dir, stop_account, stop = auxiliary(pipe, "stop")
    require(
        sha(stop_dir / "runtime.tar.zst") == held["stop_report_sha256"]
        and stop.get("stop", {}).get("verified_stopped") is True,
        "Safety-stop source differs",
    )
    protected = report["protected_base"]
    require(
        protected["run_id"] == group["run_id"]
        and protected["ref"] == group["task"]["public_base_ref"],
        "Public base identity differs",
    )
    views = log_policy.derive(group["task"], native_controls, packed)
    bindings = {
        name: sha(directory / name)
        for name in (
            "journal.json",
            "held.json",
            "submission.json",
            "accounting.json",
            "runtime.tar.zst",
            "stop/group.json",
            "stop/submission.json",
            "stop/accounting.json",
            "stop/runtime.tar.zst",
        )
    }
    summary = {
        "run_id": group["run_id"],
        "task_id": task_id,
        "task": group["task"]["task"],
        "worker_id": primary["worker_id"],
        "plan_sha256": sha(root / "plan.json"),
        "plan_identity": plan["plan_identity"],
        "original_files_sha256": bindings,
        "control_archive_sha256": outer["control-artifacts.tar.gz"]["sha256"],
        "protected_base": protected,
        "classifier_error": ERROR,
        "native_controls": diagnostics,
        "inspection_views": views,
        "scientific_acceptance": False,
        "native_reward_accepted": False,
        "terminal_cpu_admissions": [
            reconciled(pipe, "", account),
            reconciled(pipe, "stop", stop_account),
        ],
    }
    summary["source_identity"] = json_sha(summary)
    return pipe, summary
