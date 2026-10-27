"""Record this completed input-access rejection; not part of the task factory."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
ARCHIVE = PRIVATE / "archives/211"
ROWS = {
    row["path"]: row for row in json.loads((ARCHIVE / "sealed-manifest.json").read_text())["files"]
}


def original(name):
    raw = (ARCHIVE / "files" / name).read_bytes()
    assert len(raw) == ROWS[name]["bytes"]
    assert hashlib.sha256(raw).hexdigest() == ROWS[name]["sha256"]
    return raw


pipeline = json.loads(original("pipeline.json"))
outcome = json.loads(original("setup-raw/outcome.json"))
setup = json.loads(original("setup-raw/result.json"))
perf = json.loads(Path(__file__).with_name("performance-211-detail.json").read_text())
readback = json.loads((ARCHIVE / "independent-readback.json").read_text())
root = json.loads((ARCHIVE / "root-evidence/readback.json").read_text())
clean = json.loads((ARCHIVE / "fresh-provider-cleanup.json").read_text())
assert clean["complete"] and clean["fresh_original_ids_absent"] and not clean["sandboxes"]
assert pipeline["status"] == "rejected" and pipeline["rejection"]["stage"] == "setup"
assert outcome["disposition"] == "blocked" and setup["reference_tests"] == 0
logs = {
    p: original("setup-raw/operations/" + p + "/output.log").decode()
    for p in ("0009", "0014", "0023")
}
assert "Cleveland2012_pedigree.txt.gz 404" in logs["0009"]
assert "Cleveland2012_snps1000.txt.gz 404" in logs["0009"]
assert "The specified bucket does not exist" in logs["0014"] and "b''" in logs["0023"]
record = {
    "observed_at": datetime.now(UTC).isoformat(),
    "number": 211,
    "source_id": "sgkit-relatedness",
    "audited_state": "autonomous_original_input_unavailable_rejection",
    "original_pipeline_status": "rejected",
    "terminal_host_state": "SUCCEEDED",
    "operator_interventions": 0,
    "operator_scientific_edits": 0,
    "factory_runtime_revision": "da45986ee60796415f4ac4ff9dab5a98b2f54107",
    "runtime_file_count": 232,
    "source_assets_identical_to": 194,
    "elapsed_pipeline_seconds": perf["elapsed_pipeline_seconds"],
    "accounted_model_request_attempts": perf["accounted_model_request_attempts"],
    "author_provider_response_receipts": perf["author_provider_response_receipts"],
    "reference_test_requests": setup["reference_test_requests"],
    "controlled_reference_dispatches": 0,
    "native_execution_validated": False,
    "fully_qualified_task": False,
    "published": False,
    "solver_attempted": False,
    "original_archive_files": readback["file_count"],
    "original_archive_bytes": readback["total_bytes"],
    "source_archive_manifest_sha256": readback["source_manifest_sha256"],
    "all_original_files_hash_size_mode_verified": True,
    "original_root_files": root["file_count"],
    "original_root_bytes": root["bytes"],
    "complete_root_export_verified": True,
    "original_and_fresh_cleanup_verified": True,
    "cleanup_owners": len(clean["owners"]),
    "fresh_all_original_claim_ids_checked": clean["all_original_sdk_claim_ids_checked"],
    "scientific_source_broken_claimed": False,
    "no_reference_or_replay_dispatches": True,
    "input_fetches_attempted": True,
    "new_staging_precheck_exercised_on_real_notebook_inputs": False,
    "rejection_evidence": [
        {
            "path": "setup-raw/operations/" + p + "/output.log",
            "sha256": ROWS["setup-raw/operations/" + p + "/output.log"]["sha256"],
        }
        for p in logs
    ],
    "findings": [
        "Both original scientific data URLs returned404; the storage API returnedNoSuchBucket. These are recorded observations, not proof that no mirror exists anywhere.",
        "The worker did not establish a verified copy of the original inputs and blocked without substituting data, changing source calls or spending a reference dispatch.",
        "The original prose overstates the exhaustiveness of mirror searches and permanence of loss. The accepted narrow rejection is input unavailability within this recorded run, not universal nonexistence or proof of broken science.",
        "The general input-restaging precheck was not reached; its three synthetic-provider controls remain the evidence for that boundary. No fresh scientific qualification.",
    ],
    "original_pipeline_sha256": hashlib.sha256(original("pipeline.json")).hexdigest(),
    "private_claim_sha256": hashlib.sha256(
        (PRIVATE / "launch/211-submission.json").read_bytes()
    ).hexdigest(),
    "originals_modified": False,
    "rights_scope": "Operational summaries only; no unqualified task/data publication.",
}
Path(__file__).with_name("result-211.json").write_text(json.dumps(record, indent=2) + "\n")
public = EXPERIMENT / "autonomous-runs/211"
public.mkdir(exist_ok=True)
(public / "provider-cleanup.json").write_bytes(
    (ARCHIVE / "fresh-provider-cleanup.json").read_bytes()
)
(public / "original-root-readback.json").write_bytes(
    (ARCHIVE / "root-evidence/readback.json").read_bytes()
)
print(
    json.dumps(
        {
            "audited_state": record["audited_state"],
            "pipeline_minutes": round(perf["elapsed_pipeline_seconds"] / 60, 2),
            "requests": perf["accounted_model_request_attempts"],
        }
    )
)
