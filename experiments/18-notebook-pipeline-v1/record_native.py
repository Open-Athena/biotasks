"""Preserve one decoded Scanpy v2 native trial and check its validation contract.

The input is the checksum-verified text export plus the original worker log list.
This records evidence; it does not create a biological score or accept a task.
"""

import argparse
import json
import math
import shutil
from pathlib import Path


def record(export, logs, destination, expected_reward, budget_trial):
    trials = list((export / "jobs").glob("*/task__*/attempts/000/result.json"))
    if len(trials) != 1:
        raise ValueError("Expected exactly one native trial")
    trial = trials[0].parent
    result = json.loads(trials[0].read_text())
    if (result.get("agent_info") or {}).get("name") not in {"oracle", "artifact-control"}:
        raise ValueError("This recorder is only for the pinned no-model native agents")
    reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    cleanup = None
    archive = None
    for line in json.loads(logs.read_text()):
        if "BIOTASKS_CLEANUP_RESULT " in line:
            cleanup = json.loads(line.split("BIOTASKS_CLEANUP_RESULT ", 1)[1])
        if "BIOTASKS_SMOKE_ARCHIVE " in line:
            archive = json.loads(line.split("BIOTASKS_SMOKE_ARCHIVE ", 1)[1])
    if archive is None:
        raise ValueError("Worker export identity missing")
    destination.mkdir(parents=True, exist_ok=False)
    for name in [
        "result.json",
        "agent/oracle.txt",
        "verifier/grade.json",
        "verifier/reward.txt",
        "verifier/test-stdout.txt",
        "artifacts/manifest.json",
    ]:
        if (trial / name).exists():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(trial / name, target)
    probes = []
    for name in ["network-preflights.jsonl", "sandbox-resources.jsonl"]:
        rows = []
        if (export / name).exists():
            rows = [json.loads(line) for line in (export / name).read_text().splitlines()]
        for index, row in enumerate(rows):
            row.pop("id", None)
            row["environment"] = "task" if index == 0 else "verifier"
        (destination / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
        if name == "network-preflights.jsonl":
            probes = rows
    for name in ["candidate-preflight.json", "pins.json"]:
        if (export / name).exists():
            shutil.copyfile(export / name, destination / name)
    checks = {
        "no_trial_exception": result.get("exception_info") is None,
        "expected_reward": isinstance(reward, (int, float))
        and math.isclose(reward, expected_reward, abs_tol=1e-9),
        "two_offline_environments": len(probes) == 2
        and all(
            row["network_denied"]
            and not row["inference_credentials_present"]
            and not row["gpu_devices"]
            for row in probes
        ),
        "cpu_memory_limits": len(probes) == 2
        and all(
            row["resources"]["cpu.max"] == "400000 100000"
            and row["resources"]["memory.max"] == "8589934592"
            for row in probes
        ),
        "cleanup_verified": bool(cleanup)
        and len(cleanup) == 2
        and all(row["deleted"] for row in cleanup),
    }
    summary = {
        "stage": json.loads((export / "outcome.json").read_text())["stage"],
        "candidate_version": 2,
        "packaging_revision": 1,
        "model_called": False,
        "budget_trial": budget_trial,
        "reward": reward,
        "expected_reward": expected_reward,
        "counts_as_glm_success": False,
        "validation_passed": all(checks.values()),
        "checks": checks,
        "export_sha256": archive["sha256"],
        "owned_sandboxes_deleted_and_verified": sum(row["deleted"] for row in cleanup or []),
        "cleanup_follows_worker_artifact_readback": bool(cleanup),
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-reward", type=float, required=True)
    parser.add_argument("--budget-trial", type=int, required=True)
    args = parser.parse_args()
    summary = record(
        args.export, args.logs, args.destination, args.expected_reward, args.budget_trial
    )
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["validation_passed"] else 1)
