"""Continuation must retain original task identity and prior resource consumption."""

import hashlib
import json
from pathlib import Path

import pytest
from harbor.models.task.task import Task
from quality_continuation import load, remaining_config
from repo2rlenv.emitter.bundle import inspect_bundle
from test_execution_integration import bundle


def continuation(tmp_path):
    task = bundle(tmp_path)
    evidence = {}
    for role, agent, reward in (
        ("baseline", "nop", 0),
        ("oracle", "oracle", 1),
        ("rollout", "terminus-2", 1),
    ):
        path = tmp_path / f"{role}.json"
        path.write_text(
            json.dumps(
                {
                    "task_checksum": Task(task).checksum,
                    "config": {"agent": {"name": agent}},
                    "verifier_result": {"rewards": {"reward": reward}},
                }
            )
        )
        evidence[role] = path.name
    identity = inspect_bundle(task)["bundle_hash"]
    (tmp_path / "probes.json").write_text(
        json.dumps(
            {
                "bundle_hash": identity,
                "probes": [
                    {
                        "name": "fixture",
                        "kind": "wrong_solution",
                        "rationale": "Transport fixture only",
                        "evidence": [{"path": "instruction.md", "quote": "Test fixture only."}],
                        "script": "true\n",
                    }
                ],
            }
        )
    )
    (tmp_path / "cleanup.json").write_text(
        json.dumps({"complete": True, "sandboxes": [], "exact_id_state": "absent"})
    )
    plan = {
        "task": task.relative_to(tmp_path).as_posix(),
        "bundle_hash": identity,
        "evidence": evidence,
        "probes": "probes.json",
        "cleanup_reconciliation": "cleanup.json",
        "prior_requests": {"compatibility": 2, "generation": 3, "quality": 2, "solver-1": 4},
        "prior_trials": 9,
        "prior_solver_attempts": 1,
        "prior_quality_repairs": 0,
    }
    plan["files"] = {
        p.relative_to(tmp_path).as_posix(): {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "mode": p.stat().st_mode & 0o777,
        }
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    (tmp_path / "continuation.json").write_text(json.dumps(plan))
    return task, plan


def test_imports_bound_native_results_and_keeps_remaining_budgets(tmp_path):
    task, plan = continuation(tmp_path)
    imported, evidence, _ = load(tmp_path)
    assert imported == task
    assert set(evidence) == {"baseline", "oracle", "rollout", "probes"}
    config = json.loads(Path(__file__).with_name("pilot-config.json").read_text())
    remaining = remaining_config(config, plan)
    assert remaining["max_trials"] == 7
    assert remaining["max_solver_attempts"] == 1
    assert remaining["request_allowances"]["quality"]["requests"] == 22
    assert sum(v["requests"] for v in remaining["request_allowances"].values()) == 69
    assert config["max_trials"] == 16


def test_changed_scientific_task_is_not_imported(tmp_path):
    task, _ = continuation(tmp_path)
    (task / "instruction.md").write_text("Changed task")
    with pytest.raises(ValueError, match="evidence changed"):
        load(tmp_path)


def test_exhausted_attempts_are_not_reset(tmp_path):
    _, plan = continuation(tmp_path)
    plan["prior_solver_attempts"] = 2
    config = json.loads(Path(__file__).with_name("pilot-config.json").read_text())
    with pytest.raises(ValueError, match="exactly one solver slot"):
        remaining_config(config, plan)
