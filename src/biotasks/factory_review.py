"""Validate GLM review records and select a bounded next factory stage.

This module never accepts a task or supplies a scientific reward. A review is an
input to native validation, not evidence that native execution succeeded.
"""

from pathlib import Path, PurePosixPath


def next_stage(report: dict, workspace: Path, sessions_remaining: int) -> str:
    """Fail closed on malformed review evidence; never launch work implicitly."""
    if type(sessions_remaining) is not int or sessions_remaining < 0:
        raise ValueError("Invalid remaining session count")
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("Unsupported review report")
    disposition = report.get("disposition")
    if disposition not in {"ready_for_validation", "repair_required", "rejected"}:
        raise ValueError("Invalid review disposition")
    for field in ("findings", "checks_performed", "checks_pending"):
        if not isinstance(report.get(field), list):
            raise ValueError(f"Review requires {field}")

    def check_paths(paths):
        if not isinstance(paths, list) or not paths:
            raise ValueError("Missing review evidence paths")
        for value in paths:
            if not isinstance(value, str):
                raise ValueError("Evidence path must be text")
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "\\" in value:
                raise ValueError("Unsafe evidence path")
            target = workspace / value
            if not target.resolve().is_relative_to(workspace.resolve()) or not target.is_file():
                raise ValueError("Review evidence is missing or outside workspace")

    ids = set()
    blocking = False
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            raise ValueError("Invalid finding")
        for field in ("id", "description", "requirement"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise ValueError(f"Finding requires {field}")
        if finding["id"] in ids:
            raise ValueError("Duplicate finding ID")
        ids.add(finding["id"])
        if finding.get("severity") not in {"blocking", "advisory"}:
            raise ValueError("Invalid finding severity")
        blocking |= finding["severity"] == "blocking"
        check_paths(finding.get("evidence_paths"))
    failed_execution = False
    for check in report["checks_performed"]:
        if not isinstance(check, dict) or not isinstance(check.get("command"), str):
            raise ValueError("Invalid performed check")
        if type(check.get("exit_status")) is not int:
            raise ValueError("Missing check exit status")
        check_paths(check.get("evidence_paths"))
        failed_execution |= check["exit_status"] != 0
    if any(not isinstance(check, str) or not check.strip() for check in report["checks_pending"]):
        raise ValueError("Invalid pending check")
    if disposition == "rejected":
        return "rejected"
    if disposition == "repair_required" or blocking:
        return "repair" if sessions_remaining else "budget_exhausted"
    if failed_execution:
        return "verification_incomplete"
    return "native_validation"
