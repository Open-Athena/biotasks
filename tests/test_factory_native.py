import hashlib
import json
import subprocess
import sys

import pytest

from biotasks.factory_native import assess_case, native_plan, reward_for


def test_worker_cli_is_read_only_and_does_not_claim_acceptance(candidate):
    before = {str(p): p.read_bytes() for p in candidate.rglob("*") if p.is_file()}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biotasks.factory_check",
            "--stage",
            "construction",
            "--workspace",
            str(candidate),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    record = json.loads(result.stdout)
    assert record["status"] == "package_shape_valid"
    assert record["native_execution"] is False
    assert record["scientific_acceptance"] is False
    assert {str(p): p.read_bytes() for p in candidate.rglob("*") if p.is_file()} == before


def test_worker_cli_returns_actionable_missing_proposal_error(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biotasks.factory_check",
            "--stage",
            "specification",
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "invalid"
    assert "proposal.json" in json.loads(result.stdout)["reason"]


@pytest.fixture
def candidate(tmp_path):
    task = tmp_path / "task"
    task.mkdir()
    for name in [
        "instruction.md",
        "environment/Dockerfile",
        "tests/Dockerfile",
        "tests/test.sh",
        "solution/solve.sh",
    ]:
        path = task / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("Fixture only; never executed.")
    (task / "task.toml").write_text("""schema_version = "1.2"
artifacts = ["/output/table.tsv", "/output/stats.json"]
[agent]
timeout_sec = 300
[environment]
cpus = 4
memory_mb = 8192
storage_mb = 10240
allow_internet = false
[verifier]
environment_mode = "separate"
[verifier.environment]
cpus = 4
memory_mb = 8192
storage_mb = 10240
allow_internet = false
""")
    contract = {
        "schema_version": 1,
        "subgoals": [
            {"id": "first", "weight": 0.5, "description": "First analysis", "depends_on": []},
            {
                "id": "second",
                "weight": 0.5,
                "description": "Second analysis",
                "depends_on": ["first"],
            },
        ],
    }
    (task / "grading-contract.json").write_text(json.dumps(contract))
    (tmp_path / "controls").mkdir()
    controls = []
    for kind in ["correct", "alternative", "empty", "partial", "wrong", "dependency"]:
        artifacts = []
        if kind != "empty":
            for filename in ["table.tsv", "stats.json"]:
                name = f"controls/{kind}-{filename}"
                raw = kind.encode()
                (tmp_path / name).write_bytes(raw)
                artifacts.append(
                    {
                        "source": name,
                        "destination": "/output/" + filename,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
        controls.append(
            {
                "kind": kind,
                "rationale": "Test fixture for orchestration only",
                "artifacts": artifacts,
                "expected_subgoals": {
                    "first": kind in {"correct", "alternative", "partial"},
                    "second": kind in {"correct", "alternative"},
                },
            }
        )
    (task / "validation-plan.json").write_text(
        json.dumps({"schema_version": 1, "controls": controls})
    )
    return tmp_path


def test_plan_binds_multiple_control_artifacts_and_refuses_changed_bytes(candidate):
    plan = native_plan(candidate)
    assert len(plan["cases"]) == 7
    assert all(
        len(case["artifacts"]) == 2
        for case in plan["cases"]
        if case["kind"] not in {"reference", "empty"}
    )
    (candidate / "controls/wrong-table.tsv").write_text("Changed after construction")
    with pytest.raises(ValueError, match="frozen plan"):
        native_plan(candidate)


def test_native_outcome_requires_subgoal_agreement_not_just_scalar_reward():
    weights = {"a": 0.5, "b": 0.5}
    case = {"kind": "partial", "expected_subgoals": {"a": True, "b": False}}
    result = {
        "agent_info": {"name": "artifact-control"},
        "verifier_result": {"rewards": {"reward": 0.5}},
    }
    grade = {
        "schema_version": 1,
        "reward": 0.5,
        "full_success": False,
        "subgoals": {"a": False, "b": True},
    }
    assert assess_case(case, weights, result, grade)["status"] == "task_defect"
    grade["subgoals"] = case["expected_subgoals"]
    assert assess_case(case, weights, result, grade)["status"] == "passed"
    result["exception_info"] = {"exception_type": "DaytonaError"}
    assert assess_case(case, weights, result, grade)["reward"] is None
    assert assess_case(case, weights, result, grade)["status"] == "infra_error"
    result["exception_info"] = {"exception_type": "RewardFileNotFoundError"}
    assert assess_case(case, weights, result, None)["status"] == "task_defect"


def test_non_binary_or_missing_subgoal_cannot_produce_reward():
    for values in [{"a": 1, "b": True}, {"a": True}, {"a": True, "b": float("nan")}]:
        with pytest.raises(ValueError, match="binary"):
            reward_for(values, {"a": 0.5, "b": 0.5})


def test_control_cannot_overwrite_undeclared_solver_path(candidate):
    path = candidate / "task/validation-plan.json"
    plan = json.loads(path.read_text())
    plan["controls"][0]["artifacts"][0]["destination"] = "/tests/test.sh"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="undeclared"):
        native_plan(candidate)
