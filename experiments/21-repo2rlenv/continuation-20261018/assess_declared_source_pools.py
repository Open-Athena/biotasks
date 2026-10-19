"""Reconcile fixed input pools against original native metadata; run no tasks."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(metadata):
    extraction = metadata / "source-extraction-receipt.json"
    receipt = json.loads(extraction.read_text())
    for record in receipt["source_records"]:
        assert sha(ROOT / record["manifest"]) == record["manifest_sha256"]
        for item in record["extracted"]:
            path = metadata / item["path"]
            assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    sources = {}

    def read(relative):
        path = ROOT / relative
        sources[relative] = sha(path)
        return json.loads(path.read_text())

    cve = read("evidence/osv-intake/biopython.json")
    native = read("evidence/biopython-cve-01/native/result.json")
    review = read("evidence/legacy-biopython-admission-review/review.json")
    assert len(cve["records"]) == 2 and len(cve["eligible_at_native_default"]) == native["candidates"] == 1
    assert native["emitted"] == 1 and review["accepted_tasks"] == 0
    cve_review = next(row for row in review["records"] if row["pipeline"] == "cve_patches")
    history = read("evidence/r2e-gym-biopython-seqfeature-02/summary.json")
    assert history["history_pool_exhausted"] and history["materialization_attempts"] == history["eligible_candidates"] == 7
    assert history["exports"] == history["authoring_calls"] == 0
    bio_schedule = json.loads((metadata / "bio-original-schedule.json").read_text())
    assert (metadata / "bio-original-schedule.json").read_bytes() == (metadata / "bio-continuation-schedule.json").read_bytes()
    consumed_bio = []
    for label in ("bio-original", "bio-continuation"):
        generation = json.loads((metadata / (label + "-generation.json")).read_text())
        assert generation["attempted"] == len(generation["candidates"]) == 3
        consumed_bio.extend(generation["candidates"])
    assert len({row["id"] for row in consumed_bio}) == 6
    steps = {row["schedule"]["step"] for row in consumed_bio}
    assert steps == set(range(6)) and len(bio_schedule["steps"]) == 7
    for row in consumed_bio:
        assert row["schedule"] == bio_schedule["steps"][row["schedule"]["step"]]
    pending = next(step for step in bio_schedule["steps"] if step["step"] not in steps)
    alpha_schedule = json.loads((metadata / "skbio-alpha-final-schedule.json").read_text())
    alpha_final = json.loads((metadata / "skbio-alpha-final-generation.json").read_text())
    original_alpha = read("evidence/skbio-flow-author-01/issues.json")
    continued_alpha = read("continuation-20261018/skbio-flow-contrast-01/contrast-summary.json")
    alpha_bounds = read("continuation-20261018/skbio-flow-remaining-20261019-01-dispatch-manifest.json")
    alpha_ids = {row["candidate_id"] for row in original_alpha["records"]} | {row["id"] for row in continued_alpha["candidates"]}
    assert len(alpha_ids) == len(alpha_schedule["steps"]) == 5
    assert alpha_ids == set(alpha_bounds["excluded_candidate_ids"])
    assert alpha_final["attempted"] == 0 and not alpha_final["candidates"]
    gini_schedule = json.loads((metadata / "skbio-gini-final-schedule.json").read_text())
    assert len(gini_schedule["steps"]) == 3
    gini_ids = []
    for number in ("01", "02", "03"):
        generation = read(f"continuation-20261018/skbio-flow-gini-{number}/generation.json")
        assessment = read(f"continuation-20261018/skbio-flow-gini-author-{number}/instruction-review.json")
        assert generation["attempted"] == len(generation["candidates"]) == 1
        candidate = generation["candidates"][0]
        assert candidate["schedule"] == gini_schedule["steps"][int(number) - 1]
        assert not assessment["independently_admitted"] and not assessment["instruction_edited"] and not assessment["task_specific_author_feedback_supplied"]
        gini_ids.append(candidate["id"])
    rows = [
        {"unit_id": "cve_patches/native@biopython/biopython", "charged_candidates": 1,
         "declared_advisory_records": 2, "eligible_native_default_advisories": 1, "fresh_declared_candidates_remaining": 0,
         "native_exports": 1, "accepted_tasks": 0, "original_admission_decision": cve_review["decision"],
         "original_admission_reason_codes": cve_review["reason_codes"], "pending_native_export_stages": 0,
         "state": "declared_input_pool_exhausted_below_target",
         "next_action": "Report the only eligible frozen advisory's native export and unaccepted original runtime profile. Retain the original acceptance limits; no task-specific runtime/grader repair or refreshed intake is inferred."},
        {"unit_id": "commit_runtime/r2e_gym@biopython/biopython", "charged_candidates": 7,
         "declared_history_records": history["history_records_considered"], "source_filtered_records": history["source_filtered_records"],
         "fresh_declared_candidates_remaining": 0, "native_exports": 0, "author_calls": 0,
         "materialization_failures": history["failure_counts"], "pending_native_export_stages": 0,
         "state": "declared_input_pool_exhausted_below_target",
         "next_action": "Report the exhausted fixed2000-record history pool: seven materialization failures and no author call/export. Three numeric candidate slots do not authorize inventing a new declared history pool or repairing these tasks."},
        {"unit_id": "repo_reconstruct/swe_flow@biopython/biopython", "charged_candidates": 6,
         "declared_schedule_steps": 7, "consumed_candidate_ids": [row["id"] for row in consumed_bio],
         "consumed_steps": sorted(steps), "fresh_declared_candidates_remaining": 1,
         "pending_schedule_step": pending["step"], "pending_nodes": pending["nodes_to_develop"],
         "pending_native_export_stages": None, "state": "target_not_met_work_remaining",
         "next_action": "Run only original schedule step6 with all six consumed IDs excluded, under the existing frozen profile and original target/cap. No source expansion or task-specific fix; complete native author/export stages before final unchanged-output assessment."},
        {"unit_id": "repo_reconstruct/swe_flow@scikit-bio/scikit-bio", "charged_candidates": 8,
         "alpha_profile_schedule_steps": 5, "gini_profile_schedule_steps": 3,
         "consumed_alpha_ids": sorted(alpha_ids), "consumed_gini_ids": gini_ids,
         "fresh_declared_candidates_remaining": 0, "pending_native_export_stages": 3,
         "state": "source_pool_exhausted_native_stages_remaining",
         "next_action": "Complete native exporter and baseline/reference controls on the three saved original Gini author outputs without edits, to measure full native-stage outcomes. Retain their quality rejections; no new author calls or candidate charges. All eight declared profile steps are already consumed."},
    ]
    shutil.copyfile(extraction, BASE / "declared-source-pool-extraction-receipt.json")
    return {"stage": "fixed_source_pool_and_remaining_native_stage_reconciliation", "rows": rows,
            "source_record_sha256": sources, "extraction_receipt_sha256": sha(extraction),
            "new_model_calls": 0, "target_repository_code_executed": False, "task_assets_modified": False,
            "limits": ["Pool exhaustion is scoped to recorded fixed inputs/profiles, not every possible repository input.",
                       "No source allowance or native repair limit is reset.",
                       "A remaining native export stage is not counted as executed, exported, admitted or scored.",
                       "Original acceptance decisions and native rewards remain unchanged."]}


if __name__ == "__main__":
    report = assess(Path(sys.argv[1]))
    (BASE / "declared-source-pool-reconciliation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({row["unit_id"]: {"fresh_inputs": row["fresh_declared_candidates_remaining"], "pending_native_exports": row["pending_native_export_stages"]} for row in report["rows"]}))
