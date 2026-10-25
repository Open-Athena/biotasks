"""Check call-site identity coverage over sealed original sources, without executing them."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
from source_operations import operation_inventory  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    panel = json.loads((EXPERIMENT / "panel-rounds/032/current-panel-summary.json").read_text())
    assert len(panel["records"]) == 10
    records = []
    for case in panel["records"]:
        archive = args.private_root / f"archives/{case['campaign']:03}"
        raw_manifest = (archive / "sealed-manifest.json").read_bytes()
        manifest_hash = hashlib.sha256(raw_manifest).hexdigest()
        assert manifest_hash == case["source_archive_manifest_sha256"]
        readback = json.loads((archive / "independent-readback.json").read_text())
        assert readback["all_files_download_verified"]
        assert readback["source_manifest_sha256"] == manifest_hash
        entries = {r["path"]: r for r in json.loads(raw_manifest)["files"]}
        name = "preparation/prepare/input.json"
        raw = (archive / "files" / name).read_bytes()
        assert len(raw) == entries[name]["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entries[name]["sha256"]
        context = json.loads(raw)
        source = context["baseline_script"]
        assert hashlib.sha256(source.encode()).hexdigest() == context["conversion"]["script_sha256"]
        inventory = operation_inventory(source)
        calls = inventory["operations"]
        old_ids = [f"call-{r['line']}-{r['column']}" for r in calls]
        counts = Counter(old_ids)
        assert len(calls) == len({r["id"] for r in calls})
        assert all(
            r["id"] == old for r, old in zip(calls, old_ids, strict=True) if counts[old] == 1
        )
        records.append(
            {
                "campaign": case["campaign"],
                "source_id": case["source_id"],
                "domain": case["domain"],
                "original_source_archive_manifest_sha256": manifest_hash,
                "baseline_source_sha256": inventory["source_sha256"],
                "original_call_sites": len(calls),
                "legacy_unique_ids": len(counts),
                "legacy_colliding_start_positions": sum(n > 1 for n in counts.values()),
                "legacy_aliased_call_sites": len(calls) - len(counts),
                "new_distinct_ids": len({r["id"] for r in calls}),
                "unambiguous_legacy_ids_preserved": sum(n == 1 for n in counts.values()),
                "all_source_calls_retained": True,
            }
        )
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "source_operations_sha256": hashlib.sha256(
            (EXPERIMENT / "source_operations.py").read_bytes()
        ).hexdigest(),
        "panel_count": len(records),
        "sources_with_legacy_collisions": sum(r["legacy_aliased_call_sites"] > 0 for r in records),
        "all_new_source_ids_distinct": True,
        "unambiguous_legacy_ids_preserved": True,
        "source_or_generated_artifacts_changed": False,
        "scientific_execution_or_model_calls": 0,
        "scope": "Static literal call-site identity only; not runtime tracing, semantic coverage, scientific validation or proof that the collision caused any particular exclusion.",
        "records": records,
    }
    args.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({k: v for k, v in proof.items() if k != "records"}))


if __name__ == "__main__":
    main()
