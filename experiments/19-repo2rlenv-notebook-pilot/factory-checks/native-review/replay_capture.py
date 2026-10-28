"""Exercise review evidence capture on an original archive, without a model."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))

from native_review import collect, digest, recheck  # noqa: E402
from review_packet import ReviewPacket, encode  # noqa: E402


def run(native, manifest, expected_sha256, packet_root):
    if digest(manifest) != expected_sha256:
        raise ValueError("Original archive manifest identity changed")
    original = {row["path"]: row for row in json.loads(manifest.read_text())["files"]}
    evidence, trials = collect(native)
    for row in evidence["inventory"]:
        source = original["native/" + row["path"]]
        if any(row[key] != source[key] for key in ("sha256", "bytes", "mode")):
            raise ValueError("Review source differs from original archive")
    packet = ReviewPacket(packet_root, evidence, time.time() + 90)
    if packet.reconstruct() != evidence:
        raise ValueError("Review packet did not preserve original values")
    trace_keys = [key for key in evidence["documents"] if key.endswith("/agent/trajectory.json")]
    for key in trace_keys:
        pointer = "/" + key.replace("~", "~0").replace("/", "~1")
        text = evidence["documents"][key]
        lines = text.splitlines()
        response = json.loads(
            asyncio.run(
                packet.read_review_evidence(
                    field="documents",
                    pointer=pointer,
                    start_line=1,
                    end_line=max(1, len(lines)),
                    end_column=None,
                )
            )
        )
        if [item["text"] for item in response["lines"]] != lines:
            raise ValueError("Read-only tool did not serve complete recorded trajectory")
    recheck(native, evidence["inventory"])
    return {
        "scope": "Offline evidence capture/readback only; no scientific execution or model review.",
        "original_member_manifest_sha256": expected_sha256,
        "bundle_hash": evidence["bundle_hash"],
        "source_files_verified": len(evidence["inventory"]),
        "source_bytes_verified": sum(row["bytes"] for row in evidence["inventory"]),
        "complete_text_documents": len(evidence["documents"]),
        "binary_inventory_entries": sum(not row["text_available"] for row in evidence["inventory"]),
        "captured_trajectories_fully_read": len(trace_keys),
        "roles": [trial.role for trial in trials],
        "original_rewards": [trial.reward for trial in trials],
        "all_trial_bundle_hashes_match": all(
            trial.bundle_hash == evidence["bundle_hash"] for trial in trials
        ),
        "review_context_sha256": hashlib.sha256(encode(evidence)).hexdigest(),
        "review_packet_manifest_sha256": packet.manifest_sha256,
        "collector_sha256": digest(EXPERIMENT / "native_review.py"),
        "prompt_sha256": digest(
            EXPERIMENT.parents[1] / "src/biotasks/prompts/notebook-native-review.md"
        ),
        "model_review_run": False,
        "scientific_suitability_established": False,
        "original_rewards_changed": False,
        "new_model_requests": 0,
        "new_jobs_or_sandboxes": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError("Preserve the prior evidence-capture report")
    result = run(args.native, args.manifest, args.manifest_sha256, args.packet_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
