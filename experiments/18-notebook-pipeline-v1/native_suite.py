"""Execute one finite native reference/control suite through pinned Harbor.

The outer worker owns package preparation and credentials. Every case gets fresh
task/verifier sandboxes, durable read-back before cleanup, and a separate record.
Callbacks allow offline integration checks without substituting biological scores.
"""

import copy
import json

from biotasks.factory_native import assess_case, candidate_hash, isolation_checks, native_plan


def run_suite(workspace, config, output, limits, run_trial, persist, cleanup):
    """No automatic retries; task defects are auditable, infra failures ungraded."""
    ceilings = {
        "maximum_trials": 7,
        "trial_timeout_seconds": 1800,
        "reference_timeout_seconds": 600,
    }
    if set(limits) != set(ceilings) or any(
        type(limits[name]) is not int or not 1 <= limits[name] <= maximum
        for name, maximum in ceilings.items()
    ):
        raise ValueError("Native validation limits exceed fixed worker ceilings")
    if config.get("n_attempts") != 1 or config.get("retry", {}).get("max_retries") != 0:
        raise ValueError("Native suite requires one attempt and no automatic retries")
    output.mkdir(parents=True, exist_ok=False)
    candidate = candidate_hash(workspace)
    try:
        plan = native_plan(workspace)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        summary = {"status": "not_runnable", "reason": str(error), "cases": [], "model_calls": 0}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return summary
    if len(plan["cases"]) > limits["maximum_trials"]:
        raise ValueError("Native suite exceeds frozen trial budget")
    rows = []
    for case in plan["cases"]:
        case_root = output / case["id"]
        case_root.mkdir()
        trial = copy.deepcopy(config)
        trial.update(
            job_name=case["id"],
            jobs_dir=str(case_root / "jobs"),
            trial_attempt_timeout_sec=limits["trial_timeout_seconds"],
        )
        trial["agents"] = [
            {"name": "oracle", "override_timeout_sec": limits["reference_timeout_seconds"]}
        ]
        if case["kind"] != "reference":
            trial["agents"] = [
                {
                    "import_path": "control_agent:ArtifactControlAgent",
                    "override_timeout_sec": 60,
                    "override_setup_timeout_sec": 60,
                    "kwargs": {
                        "artifacts": [
                            {
                                "source": str(workspace / artifact["source"]),
                                "destination": artifact["destination"],
                            }
                            for artifact in case["artifacts"]
                        ]
                    },
                }
            ]
        (case_root / "harbor-job.json").write_text(json.dumps(trial, indent=2) + "\n")
        (case_root / "expected.json").write_text(json.dumps(case, indent=2) + "\n")
        try:
            run_trial(case_root, limits["trial_timeout_seconds"] + 120)
            results = list((case_root / "jobs").glob("*/*/attempts/000/result.json"))
            if len(results) != 1:
                raise ValueError("Exactly one native trial result is required")
            result = json.loads(results[0].read_text())
            grade_path = results[0].parent / "verifier/grade.json"
            grade = json.loads(grade_path.read_text()) if grade_path.is_file() else None
            row = assess_case(case, plan["weights"], result, grade)
            checks = isolation_checks(case_root)
            row["checks"] = checks
            if not all(checks.values()):
                row.update(status="infra_error", reason="Native isolation evidence is incomplete")
        except Exception as error:
            row = {"status": "infra_error", "reason": type(error).__name__, "reward": None}
        row["id"] = case["id"]
        (case_root / "assessment.json").write_text(json.dumps(row, indent=2) + "\n")
        # Storage failure deliberately prevents teardown. Never discard evidence
        # merely because Harbor itself returned an exception or a timeout.
        persist(case_root, case["id"])
        try:
            cleanup(case_root)
            removed = json.loads((case_root / "cleanup.json").read_text())
            if not removed or not all(item["deleted"] for item in removed):
                raise ValueError("Native sandbox cleanup incomplete")
        except Exception as error:
            row.update(status="infra_error", cleanup_error=type(error).__name__)
        (case_root / "assessment.json").write_text(json.dumps(row, indent=2) + "\n")
        persist(case_root, case["id"])
        rows.append(row)
        if row["status"] in {"infra_error", "incomplete"}:
            break
    status = "passed" if all(row["status"] == "passed" for row in rows) else "task_defect"
    if any(row["status"] in {"infra_error", "incomplete"} for row in rows):
        status = "infra_error"
    summary = {
        "schema_version": 1,
        "status": status,
        "cases": rows,
        "model_calls": 0,
        "plan_sha256": plan["plan_sha256"],
        "contract_sha256": plan["contract_sha256"],
        "disk_quota_verified": False,
        "candidate_sha256": candidate,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
