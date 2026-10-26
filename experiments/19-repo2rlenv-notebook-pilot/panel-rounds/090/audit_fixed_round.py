"""Bind fixed-round outcomes to original inputs, sealed readbacks and cleanup.

Metadata and small frozen input archives only. No provider/model/scientific calls
and no repeated biological archive readback; prior readback receipts stay explicit.
"""

import argparse
import hashlib
import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def audit(private):
    panel = load(Path(__file__).with_name("development-panel.json"))
    assert len(panel["cases"]) == 10
    baseline = None
    counts = {
        "generated_candidate_rejections": 0,
        "source_fidelity_rejections": 0,
        "infrastructure_failures": 0,
    }
    records = []
    for case in panel["cases"]:
        number = case["campaign"]
        result_path = (Path(__file__).parent / case["result"]).resolve()
        result = load(result_path)
        freeze = load(result_path.parent / f"freeze-{number}.json")
        identity = load(result_path.parent / "runtime-identity.json")["runtime_files"]
        assert len(identity) == panel["runtime_file_count"] == 224
        if baseline is None:
            baseline = identity
        assert identity == baseline
        assert freeze["public_runtime_revision"] == panel["public_runtime_revision"]
        claim_path = private / f"launch/{number}-submission.json"
        claim_raw = claim_path.read_bytes()
        claim = json.loads(claim_raw)
        payload = private / f"launch/{number}-payload"
        input_raw = (payload / "inputs.json").read_bytes()
        inputs = json.loads(input_raw)
        assert digest(input_raw) == freeze["input_manifest_sha256"]
        assert inputs["factory_revision"] == freeze["input_revision"]
        assert inputs["files"] == claim["inputs"]["files"] == freeze["payload_files"]
        packet_raw = (payload / "biotasks.tar").read_bytes()
        assert digest(packet_raw) == inputs["files"]["biotasks.tar"]
        actual = {}
        with tarfile.open(fileobj=io.BytesIO(packet_raw)) as archive:
            for member in archive:
                if member.isfile():
                    actual[member.name] = hashlib.file_digest(
                        archive.extractfile(member), "sha256"
                    ).hexdigest()
        assert actual == {**identity, **freeze["source_assets"]}
        archive_root = private / f"archives/{number}"
        manifest_raw = (archive_root / "sealed-manifest.json").read_bytes()
        manifest_sha = digest(manifest_raw)
        readback = load(archive_root / "independent-readback.json")
        root = load(archive_root / "root-evidence/readback.json")
        assert (
            readback["all_files_download_verified"]
            and root["all_manifest_files_hash_size_mode_verified"]
        )
        assert (
            readback["source_manifest_sha256"]
            == result["source_archive_manifest_sha256"]
            == manifest_sha
        )
        pipeline_raw = (archive_root / "files/pipeline.json").read_bytes()
        row = next(
            row for row in json.loads(manifest_raw)["files"] if row["path"] == "pipeline.json"
        )
        assert digest(pipeline_raw) == row["sha256"] and len(pipeline_raw) == row["bytes"]
        pipeline = json.loads(pipeline_raw)
        assert pipeline["operator_interventions"] == 0
        assert pipeline["status"] == result["original_pipeline_status"]
        clean_raw = (EXP / f"autonomous-runs/{number}/provider-cleanup.json").read_bytes()
        clean = json.loads(clean_raw)
        assert clean["complete"] and clean["original_all_cleanup_passed"]
        assert clean["fresh_original_ids_absent"] and not clean["sandboxes"]
        assert clean["source_archive_manifest_sha256"] == manifest_sha
        assert clean["source_configuration_sha256"] == inputs["files"]["campaign-config.json"]
        observations = [
            load(p) for p in (private / "launch/typed-observations").glob(f"{number}-*.json")
        ]
        terminal = max(observations, key=lambda item: item["observed_at"])
        assert terminal["terminal"] and terminal["claim_sha256"] == digest(claim_raw)
        assert terminal["state"] == result["terminal_host_state"]
        if pipeline["status"] == "infrastructure_failed":
            counts["infrastructure_failures"] += 1
        else:
            assert pipeline["status"] == "rejected"
            key = (
                "source_fidelity_rejections"
                if case["state"] == "autonomous_source_fidelity_rejection"
                else "generated_candidate_rejections"
            )
            counts[key] += 1
        assert not result["fully_qualified_task"] and not result["published"]
        records.append(
            {
                "campaign": number,
                "result_sha256": digest(result_path.read_bytes()),
                "claim_sha256": digest(claim_raw),
                "frozen_input_manifest_sha256": digest(input_raw),
                "science_manifest_sha256": manifest_sha,
                "root_readback_sha256": digest(
                    (archive_root / "root-evidence/readback.json").read_bytes()
                ),
                "cleanup_sha256": digest(clean_raw),
                "owners_verified_absent": len(clean["owners"]),
                "original_status": pipeline["status"],
            }
        )
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": __doc__,
        "runtime_revision": panel["public_runtime_revision"],
        "runtime_files": len(baseline),
        "cases": len(records),
        "counts": counts,
        "qualified_tasks": 0,
        "input_maps_identical": True,
        "all_original_readback_and_cleanup_bindings_verified": True,
        "new_provider_model_or_scientific_calls": 0,
        "records": records,
        "does_not_prove_pipeline_readiness": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    report = audit(args.private_root)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"records", "scope"}}))
