"""Compare retained runtime inputs with original PR-diff exports; execute no task code."""

import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prdiff_runtime_input import NETWORK_APPEND, TOOLING_APPEND  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(private_root):
    original_path = ROOT / "evidence/pr-diff-01/bundle-files-sha256.json"
    original = json.loads(original_path.read_text())
    rows = []
    sources = []
    caveats = []
    for cohort in ("biopython", "skbio", "bedtools", "deseq"):
        manifest_path = ROOT / f"hf-prdiff-{cohort}-provider-01-snapshot-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        receipts = {f["path"]: f for f in manifest["files"]}
        folder = private_root / f"prdiff-{cohort}-provider-dispatch-01"
        verified = {}
        for name in ("cohort-tasks.tar.gz", "cohort.json"):
            data = (folder / name).read_bytes()
            receipt = receipts[f"frozen-inputs/{name}"]
            assert len(data) == receipt["bytes"] and sha(data) == receipt["sha256"]
            verified[name] = receipt["sha256"]
        inputs = json.loads((folder / "cohort.json").read_text())
        if manifest["cohort"] != cohort:
            caveats.append({"manifest": manifest_path.name, "declared_cohort": manifest["cohort"], "actual_inputs": cohort})
        with tarfile.open(folder / "cohort-tasks.tar.gz") as archive:
            members = archive.getmembers()
            assert sum(member.size for member in members) < 4 * 1024**2
            files = {member.name: archive.extractfile(member).read() for member in members if member.isfile()}
            assert not any(member.issym() or member.islnk() for member in members)
            for item in inputs["tasks"]:
                review = json.loads(files[item["review"]])
                assert review["task"] == item["task"]
                prefix = item["path"] + "/"
                assets = {name.removeprefix(prefix): data for name, data in files.items() if name.startswith(prefix)}
                assert set(assets) == set(review["asset_sha256"]) == set(review["runtime_asset_sha256"])
                original_assets = {}
                changed = []
                for name, data in assets.items():
                    assert sha(data) == review["runtime_asset_sha256"][name]
                    if name in ("environment/Dockerfile", "task.toml"):
                        suffix = (TOOLING_APPEND if name == "environment/Dockerfile" else NETWORK_APPEND).encode()
                        assert data.endswith(suffix)
                        data = data[:-len(suffix)]
                        changed.append(name)
                    expected = original[f"{review['repository'].replace('/', '__')}/{item['task']}/{name}"]
                    assert sha(data) == review["asset_sha256"][name] == expected
                    original_assets[name] = expected
                rows.append({
                    "task": item["task"], "repository": review["repository"], "base": review["base"],
                    "original_export_assets_verified": len(original_assets),
                    "original_instruction_reference_and_grader_unchanged": True,
                    "runtime_changed_assets": sorted(changed),
                    "runtime_changes": "Only identical fixed tmux-install and no-network suffixes; no other asset changes.",
                    "original_asset_sha256": original_assets,
                    "stock_runtime_success_established_by_this_audit": False,
                    "audit_executes_task_code": False,
                })
        sources.append({"manifest": manifest_path.name, "manifest_sha256": sha(manifest_path.read_bytes()), "verified_input_sha256": verified})
    assert len(rows) == 12
    return {
        "stage": "post_run_read_only_original_export_provenance_assessment",
        "task_count": len(rows), "original_asset_count": sum(r["original_export_assets_verified"] for r in rows),
        "automatic_content_unchanged_tasks": len(rows), "task_specific_content_fixes_found": 0,
        "shared_runtime_suffix_adaptations_per_task": 2,
        "primary_interpretation": "Automatic PR-diff content is proven unchanged for all 12 selected legacy tasks. Their recorded runtime results use a separately declared shared tmux/offline profile, not the original unadapted export runtime. No new task admission or solver result is created.",
        "original_asset_manifest": str(original_path.relative_to(ROOT)),
        "original_asset_manifest_sha256": sha(original_path.read_bytes()),
        "source_inputs": sources, "rows": rows,
        "historical_metadata_caveats": caveats,
        "limits": ["Byte provenance is not a functional-correctness proof.", "This audit does not establish unattended input selection or original stock-runtime success.", "Historical cohort-label metadata errors remain preserved; inputs are identified by verified archive and task hashes.", "No task assets were edited or executed, and no author feedback was supplied."],
    }


if __name__ == "__main__":
    report = audit(Path(sys.argv[1]))
    target = Path(__file__).with_name("prdiff-original-asset-provenance-assessment.json")
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("task_count", "original_asset_count", "automatic_content_unchanged_tasks", "task_specific_content_fixes_found")}))
