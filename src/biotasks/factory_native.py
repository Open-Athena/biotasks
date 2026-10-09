"""Machine-readable native checks authored by GLM, executed by the factory.

The host checks contract consistency and compares executable observations. It
does not invent scientific controls, reference answers, or repair instructions.
"""

import hashlib
import json
import math
import re
import tomllib
from pathlib import Path, PurePosixPath

CONTROL_KINDS = {"correct", "alternative", "empty", "partial", "wrong", "dependency"}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_hash(workspace: Path) -> str:
    files = []
    if (workspace / "task").is_symlink():
        raise ValueError("Candidate symlinks are unsupported")
    for path in sorted((workspace / "task").rglob("*")):
        if path.is_symlink():
            raise ValueError("Candidate symlinks are unsupported")
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(workspace / "task")),
                    "size": path.stat().st_size,
                    "sha256": file_hash(path),
                }
            )
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def local_file(workspace: Path, name: str) -> Path:
    path = PurePosixPath(name)
    target = workspace / name
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or (not target.is_file() or not target.resolve().is_relative_to(workspace.resolve()))
    ):
        raise ValueError("Missing or unsafe validation asset")
    return target


def subgoal_weights(contract: dict) -> dict[str, float]:
    goals = contract.get("subgoals")
    if (
        contract.get("schema_version") != 1
        or not isinstance(goals, list)
        or not 2 <= len(goals) <= 4
    ):
        raise ValueError("Expected two to four scientific subgoals")
    weights = {}
    for goal in goals:
        identity, weight = goal.get("id"), goal.get("weight")
        dependencies = goal.get("depends_on")
        if (
            not isinstance(identity, str)
            or not re.fullmatch(r"[a-zA-Z0-9_-]+", identity)
            or identity in weights
        ):
            raise ValueError("Invalid or duplicate scientific subgoal")
        if type(weight) not in (int, float) or not 0 < weight <= 1:
            raise ValueError("Invalid scientific weight")
        if not isinstance(goal.get("description"), str) or not goal["description"].strip():
            raise ValueError("Missing scientific subgoal description")
        if not isinstance(dependencies, list) or any(
            not isinstance(name, str) or name not in weights for name in dependencies
        ):
            raise ValueError("Dependencies must refer to earlier subgoals")
        weights[identity] = float(weight)
    if not math.isclose(sum(weights.values()), 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Scientific weights must sum to one")
    return weights


def reward_for(subgoals: object, weights: dict[str, float]) -> float:
    if (
        not isinstance(subgoals, dict)
        or set(subgoals) != set(weights)
        or any(type(value) is not bool for value in subgoals.values())
    ):
        raise ValueError("Expected one binary outcome per scientific subgoal")
    return sum(weight for name, weight in weights.items() if subgoals[name])


def native_plan(workspace: Path) -> dict:
    """Validate package/plan shape and hash-bound controls before reserving trials."""
    task = workspace / "task"
    contract = json.loads(local_file(workspace, "task/grading-contract.json").read_text())
    weights = subgoal_weights(contract)
    plan = json.loads(local_file(workspace, "task/validation-plan.json").read_text())
    config = tomllib.loads(local_file(workspace, "task/task.toml").read_text())
    for name in (
        "instruction.md",
        "environment/Dockerfile",
        "solution/solve.sh",
        "tests/test.sh",
        "tests/Dockerfile",
    ):
        local_file(workspace, "task/" + name)
    if config.get("schema_version") != "1.2" or config.get("agent", {}).get("timeout_sec") != 300:
        raise ValueError("Task requires pinned Harbor format and 300-second solver limit")
    if config.get("verifier", {}).get("environment_mode") != "separate":
        raise ValueError("A separate verifier environment is required")
    for environment in (
        config.get("environment", {}),
        config.get("verifier", {}).get("environment", {}),
    ):
        for key, ceiling in (("cpus", 4), ("memory_mb", 8192), ("storage_mb", 10240)):
            value = environment.get(key)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("Task exceeds or omits the resource profile")
        if environment.get("gpus", 0) != 0 or environment.get("allow_internet") is not False:
            raise ValueError("Native execution must be offline and CPU only")
    outputs = config.get("artifacts")
    if (
        not isinstance(outputs, list)
        or not outputs
        or any(
            not isinstance(name, str)
            or not PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
            or name == "/"
            or PurePosixPath(name).parts[1] in {"tests", "solution", "logs", "proc", "sys", "dev"}
            for name in outputs
        )
    ):
        raise ValueError("Declare exact absolute solver artifact paths")
    if plan.get("schema_version") != 1 or not isinstance(plan.get("controls"), list):
        raise ValueError("Missing native validation plan")
    controls = plan["controls"]
    if (
        len(controls) != len(CONTROL_KINDS)
        or {case.get("kind") for case in controls} != CONTROL_KINDS
    ):
        raise ValueError("Exactly one control of each required kind is needed")
    cases = [
        {
            "id": "reference",
            "kind": "reference",
            "artifacts": [],
            "expected_subgoals": dict.fromkeys(weights, True),
        }
    ]
    for case in controls:
        kind = case["kind"]
        expected = case.get("expected_subgoals")
        reward = reward_for(expected, weights)
        if kind in {"correct", "alternative"} and not all(expected.values()):
            raise ValueError("Valid controls must pass every subgoal")
        if kind == "empty" and any(expected.values()):
            raise ValueError("Empty submission cannot receive scientific credit")
        if kind == "partial" and not 0 < reward < 1:
            raise ValueError("Partial control must receive partial credit")
        if kind in {"wrong", "dependency"} and all(expected.values()):
            raise ValueError("Incorrect controls must fail a scientific subgoal")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            raise ValueError("Controls require a scientific rationale")
        artifacts = case.get("artifacts")
        if not isinstance(artifacts, list) or (kind == "empty") != (not artifacts):
            raise ValueError("Only the empty control has no submitted artifacts")
        seen = set()
        for artifact in artifacts:
            source = local_file(workspace, artifact["source"])
            destination = artifact["destination"]
            if destination not in outputs or destination in seen:
                raise ValueError("Control destination is undeclared or duplicated")
            seen.add(destination)
            if file_hash(source) != artifact.get("sha256"):
                raise ValueError("Control differs from the candidate's frozen plan")
        cases.append({**case, "id": kind})
    return {
        "schema_version": 1,
        "weights": weights,
        "cases": cases,
        "plan_sha256": file_hash(task / "validation-plan.json"),
        "contract_sha256": file_hash(task / "grading-contract.json"),
    }


def assess_case(case: dict, weights: dict[str, float], result: dict, grade: dict | None) -> dict:
    """Compare native Harbor evidence; infrastructure exceptions stay ungraded."""
    exception = result.get("exception_info")
    if exception is not None or result.get("secondary_exception_info"):
        kind = (exception or {}).get("exception_type")
        status = (
            "task_defect"
            if kind
            in {
                "RewardFileNotFoundError",
                "RewardFileEmptyError",
                "RewardFileInvalidError",
                "AgentTimeoutError",
                "VerifierTimeoutError",
            }
            else "infra_error"
        )
        return {"status": status, "reason": "Native trial raised an exception", "reward": None}
    agent = result.get("agent_info") or {}
    expected_agent = "oracle" if case["kind"] == "reference" else "artifact-control"
    if agent.get("name") != expected_agent or agent.get("model_info") is not None:
        return {
            "status": "incomplete",
            "reason": "Native agent identity is unverified",
            "reward": None,
        }
    if grade is None:
        return {
            "status": "incomplete",
            "reason": "Per-subgoal verifier evidence is missing",
            "reward": None,
        }
    try:
        reward = reward_for(grade.get("subgoals"), weights)
        reported = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        matches = (
            grade.get("schema_version") == 1
            and grade["subgoals"] == case["expected_subgoals"]
            and isinstance(reported, (int, float))
            and not isinstance(reported, bool)
            and math.isclose(reward, reported, rel_tol=0, abs_tol=1e-9)
            and type(grade.get("reward")) in (int, float)
            and math.isclose(reward, grade["reward"], rel_tol=0, abs_tol=1e-9)
            and grade.get("full_success") is all(grade["subgoals"].values())
        )
    except (ValueError, TypeError, KeyError):
        return {
            "status": "task_defect",
            "reason": "Invalid deterministic grading contract",
            "reward": None,
        }
    return {
        "status": "passed" if matches else "task_defect",
        "reward": reward,
        "subgoals": grade["subgoals"],
        "expected_subgoals": case["expected_subgoals"],
    }


def isolation_checks(case_root):
    probes = case_root / "network-preflights.jsonl"
    resources = case_root / "sandbox-resources.jsonl"
    if not probes.is_file() or not resources.is_file():
        return {"isolation_recorded": False}
    rows = [json.loads(line) for line in probes.read_text().splitlines()]
    allocations = [json.loads(line) for line in resources.read_text().splitlines()]
    return {
        "two_isolated_environments": len(rows) == 2
        and len(allocations) == 2
        and len({row.get("id") for row in rows}) == 2
        and all(row.get("id") for row in rows)
        and {row.get("id") for row in rows} == {row.get("id") for row in allocations},
        "offline_cpu_only": all(
            row["network_denied"] is True
            and not row["inference_credentials_present"]
            and not row["gpu_devices"]
            for row in rows
        ),
        "bounded_cpu_memory": all(
            row["resources"]["cpu.max"] != "max"
            and row["resources"]["cpu.max"].split()[0] != "max"
            and 0
            < int(row["resources"]["cpu.max"].split()[0])
            / int(row["resources"]["cpu.max"].split()[1])
            <= 4
            and 0 < int(row["resources"]["memory.max"]) <= 8589934592
            for row in rows
        ),
        "requested_disk_within_profile": all(
            0 < row["requested_storage_mb"] <= 10240 for row in allocations
        ),
    }


def assess_saved_suite(workspace: Path, directory: Path) -> dict:
    """Recheck saved native outputs before routing to a GLM audit or acceptance.

    Directory bytes must already be recovered through the artifact hash manifest.
    A saved summary's status is insufficient: re-evaluate each native result and
    grade, verify the expected controls, candidate identity, and cleanup records.
    """
    summary = json.loads((directory / "summary.json").read_text())
    if summary.get("candidate_sha256") != candidate_hash(workspace):
        raise ValueError("Native suite belongs to a different candidate")
    if summary.get("status") == "not_runnable":
        # Reproduce the static failure rather than trusting a claimed rejection.
        try:
            native_plan(workspace)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return {
                "status": "not_runnable",
                "cases": [],
                "candidate_sha256": summary["candidate_sha256"],
            }
        raise ValueError("Saved static rejection does not match this candidate")
    plan = native_plan(workspace)
    if any(summary.get(key) != plan[key] for key in ("plan_sha256", "contract_sha256")):
        raise ValueError("Native plan identity mismatch")
    rows = []
    for case in plan["cases"]:
        root = directory / case["id"]
        try:
            if json.loads((root / "expected.json").read_text()) != case:
                raise ValueError("Native expectations differ from the frozen plan")
            paths = list((root / "jobs").glob("*/*/attempts/000/result.json"))
            if len(paths) != 1:
                raise ValueError("Missing or duplicated native trial")
            result = json.loads(paths[0].read_text())
            grade_path = paths[0].parent / "verifier/grade.json"
            grade = json.loads(grade_path.read_text()) if grade_path.is_file() else None
            row = assess_case(case, plan["weights"], result, grade)
            checks = isolation_checks(root)
            row["checks"] = checks
            if not all(checks.values()):
                row.update(status="infra_error", reason="Native isolation evidence is incomplete")
            cleanup = json.loads((root / "cleanup.json").read_text())
            if len(cleanup) != 2 or not all(item["deleted"] is True for item in cleanup):
                row.update(status="infra_error", reason="Native cleanup is unverified")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            row = {"status": "incomplete", "reason": str(error)}
        rows.append({"id": case["id"], **row})
    status = "passed"
    if any(row["status"] != "passed" for row in rows):
        status = "task_defect"
    if any(row["status"] == "infra_error" for row in rows):
        status = "infra_error"
    if any(row["status"] == "incomplete" for row in rows):
        status = "incomplete"
    return {"status": status, "cases": rows, "candidate_sha256": summary["candidate_sha256"]}
