"""Accept an unchanged candidate from native evidence and a completed GLM audit.

No solver outcome enters this gate. Host checks validate executable outcomes and
resource observations; the versioned GLM audit supplies scientific assessment.
"""

import json
from pathlib import Path

from biotasks.factory_native import assess_saved_suite, candidate_hash, local_file
from biotasks.factory_review import next_stage

AUDIT_REQUIREMENTS = {
    "scientific_contract",
    "lineage_and_terms",
    "alternative_solutions",
    "solver_asset_separation",
    "methodology_and_tolerances",
}


def acceptance(workspace: Path, native_directory: Path, report: dict, integrity: dict) -> dict:
    """Return a recorded disposition; do not launch or grade a solver attempt."""
    candidate = candidate_hash(workspace)
    result = {
        "schema_version": 1,
        "candidate_sha256": candidate,
        "status": "verification_incomplete",
        "reasons": [],
    }
    if (
        integrity.get("candidate_unchanged") is not True
        or integrity.get("candidate_sha256") != candidate
    ):
        result["reasons"].append("Audit candidate identity or immutability is unverified")
        return result
    action = next_stage(report, workspace, 0)
    if action == "rejected":
        result.update(status="rejected", reasons=["GLM audit rejected this candidate"])
        return result
    if action != "native_validation" or report["checks_pending"]:
        result["reasons"].append("Scientific audit is incomplete or requires repair")
        return result
    checks = report.get("acceptance_checks")
    if not isinstance(checks, dict) or set(checks) != AUDIT_REQUIREMENTS:
        result["reasons"].append("Scientific audit coverage is incomplete")
        return result
    for name, check in checks.items():
        if check.get("status") != "satisfied" or not check.get("rationale"):
            result["reasons"].append(f"Unresolved scientific audit: {name}")
        paths = check.get("evidence_paths")
        if not isinstance(paths, list) or not paths:
            result["reasons"].append(f"Missing audit evidence: {name}")
        else:
            for path in paths:
                local_file(workspace, path)
    native = assess_saved_suite(workspace, native_directory)
    result["native_status"] = native["status"]
    if native["status"] != "passed":
        result["reasons"].append("Native reference/control suite has not passed")
        return result
    # Backend-reported allocation and sandbox-specific usage must agree. A host
    # filesystem size or requested allocation alone does not establish this.
    for case in native["cases"]:
        rows = [
            json.loads(line)
            for line in (native_directory / case["id"] / "sandbox-resources.jsonl")
            .read_text()
            .splitlines()
        ]
        for row in rows:
            allocation = row.get("backend_disk_gib")
            samples = row.get("backend_metrics")
            if type(allocation) not in (int, float) or not 0 < allocation <= 10 or not samples:
                result["reasons"].append(f"Unverified disk allocation/usage: {case['id']}")
                continue
            if any(
                not (0 <= sample["disk_used"] <= sample["disk_total"] <= allocation * 1024**3)
                or sample["disk_total"] == 0
                for sample in samples
            ):
                result["reasons"].append(
                    f"Disk metrics do not establish the sandbox budget: {case['id']}"
                )
            peak = (row.get("measurements") or {}).get("memory.peak")
            if peak is None or not 0 < int(peak) <= 8589934592:
                result["reasons"].append(
                    f"Peak memory is unverified or exceeds budget: {case['id']}"
                )
    if not result["reasons"]:
        result.update(
            status="accepted",
            baseline="pending_fresh_attempt",
            disk_measurement="highest observed backend sample; not an exact continuous peak",
        )
    return result
