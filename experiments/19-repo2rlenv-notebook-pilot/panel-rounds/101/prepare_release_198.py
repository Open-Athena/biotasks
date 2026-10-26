"""Stage operator metadata for the accepted, unchanged MDAnalysis bundle.

This is publication bookkeeping, not task construction or scientific repair.
Original task bytes and the already verified export seal remain unchanged.
"""

import hashlib
import json
import os
import tarfile
from datetime import UTC, datetime
from pathlib import Path

BASE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
ARCHIVE = BASE / "archives/198"
FILES = ARCHIVE / "files"
OUTPUT = BASE / "release198"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    raw = (json.dumps(value, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)


def main():
    assert not OUTPUT.exists()
    readback = json.loads((ARCHIVE / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"] is True
    assert digest(ARCHIVE / "sealed-manifest.json") == readback["source_manifest_sha256"]
    clean = json.loads((ARCHIVE / "fresh-provider-cleanup.json").read_text())
    assert clean["complete"] and clean["original_all_cleanup_passed"]
    assert clean["fresh_original_ids_absent"] and clean["all_original_sdk_claim_ids_checked"]
    assert len(clean["owners"]) == 7 and not clean["sandboxes"]
    pipeline = json.loads((FILES / "pipeline.json").read_text())
    assert pipeline["status"] == "validated" and pipeline["operator_interventions"] == 0
    native = json.loads((FILES / "native/result.json").read_text())
    assert native["publication_ready"] is True
    task = FILES / "native/tasks/autonomous-panel-198"
    notices = json.loads((task / "environment/SOURCE-LICENSES.json").read_text())
    expected = {Path(row["source_url"]).name: row for row in notices["reviewed_inputs"]}
    inputs = task / "environment/inputs"
    assert {path.name for path in inputs.iterdir()} == set(expected)
    actual = []
    for path in sorted(inputs.iterdir()):
        assert path.is_file() and not path.is_symlink()
        row = expected[path.name]
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"]
        actual.append(
            {
                "path": path.name,
                "bytes": row["bytes"],
                "sha256": row["sha256"],
                "source_url": row["source_url"],
            }
        )
    primary = json.loads((BASE / "release-conditions/198/primary-source-refresh.json").read_text())
    primary_by_name = {row["name"]: row for row in primary["primary_sources"]}
    assert primary_by_name["notebook-license"]["sha256"] == notices["notebook_license"]["sha256"]
    source_data = notices["data_license"]["sources"][0]
    assert (
        primary_by_name["testsuite-license"]["sha256"] == source_data["distribution_license_sha256"]
    )
    assert primary_by_name["testsuite-readme"]["sha256"] == source_data["package_readme_sha256"]
    assert "pinned-data-policy" in primary_by_name
    OUTPUT.mkdir(mode=0o700)
    rights = {
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": "Exact unchanged native input identities only; no new data or scientific execution.",
        "inputs": actual,
        "notebook_source_sha256": notices["notebook_source_sha256"],
        "primary_sources": primary["primary_sources"],
        "decision": "Retain the existing full notebook and MDAnalysisTests distribution notices, source URLs and attribution for these exact unmodified test inputs. No relicense or blanket commercial-training grant is inferred.",
        "historical_unassessed_intake_flag_preserved": True,
        "historical_flag_superseded_for_these_exact_inputs_by_this_review": True,
        "task_bundle_edited": False,
        "new_models_hosts_sandboxes": 0,
    }
    save(OUTPUT / "input-notice-review.json", rights)
    # The release helper expects paths relative to the original export seal.
    # A separate hardlink view supplies that layout without changing the archive.
    context = OUTPUT / "original-export-view"
    context.mkdir()
    raw = (ARCHIVE / "sealed-manifest.json").read_bytes()
    (context / "export-manifest.json").write_bytes(raw)
    manifest = json.loads(raw)
    linked = []
    for row in manifest["files"]:
        name = row["path"]
        if name != "pipeline.json" and not name.startswith("native/"):
            continue
        source = FILES / name
        assert source.is_file() and not source.is_symlink()
        assert source.stat().st_size == row["bytes"] and digest(source) == row["sha256"]
        assert source.stat().st_mode & 0o777 == row["mode"]
        target = context / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        linked.append(name)
    save(
        OUTPUT / "original-view.json",
        {
            "original_export_manifest_sha256": digest(ARCHIVE / "sealed-manifest.json"),
            "view_manifest_sha256": digest(context / "export-manifest.json"),
            "linked_original_files": linked,
            "source_data_modified": False,
            "scope": "Read-only original-file hardlink view; no absent seal reconstructed.",
        },
    )
    payload = BASE / "launch/198-payload"
    campaign = json.loads((payload / "campaign-config.json").read_text())
    with tarfile.open(payload / "biotasks.tar") as source:
        raw_seed = source.extractfile(
            "experiments/19-repo2rlenv-notebook-pilot/" + campaign["seed_file"]
        ).read()
    seeds = json.loads(raw_seed)
    assert seeds == [pipeline["source"]]
    (OUTPUT / "original-seed.json").write_bytes(raw_seed)
    config = {
        "revision": "23fd6d275b8d7bafca6186595bbd0e18668c8bcf",
        "native": str(context / "native"),
        "task": str(task),
        "grading": str(FILES / "grading"),
        "materialization": str(FILES / "materialization"),
        "stage": str(OUTPUT / "staged"),
        "labeled": str(OUTPUT / "labeled"),
        "plan": str(OUTPUT / "release-plan.json"),
        "autonomous_pipeline": str(context / "pipeline.json"),
        "autonomous_archive_manifest": str(context / "export-manifest.json"),
        "aggregate_authorized_usd": "200.00",
        "release_metadata": {
            "repo_id": "gonzalobenegas/biotasks-notebook-pilot-issue-19-mdanalysis-rmsd",
            "title": "AdK RMSD analysis from an MDAnalysis source notebook",
            "description": "One task reproducing five source-grounded RMSD analyses of an adenylate kinase simulation. Original scientific inputs and methods are preserved; validated output tables, native controls and one blind GLM solver attempt accompany the task.",
            "methodology": "Autonomous original-notebook intake and append-only exports, dependency/input setup, offline reference replay, task construction and independent scientific controls with source/comparison/answer-isolation review. Native Harbor oracle/no-op/solver rewards are 1/0/1. All LLM roles use GLM-5.3, with native high requested and served effort unverified. No operator scientific edits. This uses the BioTasks artifact workflow rather than the standard upstream quality-loop acceptance profile.",
            "licenses_file": str(task / "environment/SOURCE-LICENSES.json"),
            "seed_file": str(OUTPUT / "original-seed.json"),
            "citations": [
                "https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb",
                "https://github.com/MDAnalysis/mdanalysis/tree/release-2.8.0/testsuite/MDAnalysisTests/data",
                "https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/testing.rst#using-test-data-files",
                "https://github.com/Open-Athena/biotasks/issues/19",
                "https://huggingface.github.io/Repo2RLEnv/",
            ],
            "evidence_documents": {
                "input-notice-review.json": {
                    "path": str(OUTPUT / "input-notice-review.json"),
                    "sha256": digest(OUTPUT / "input-notice-review.json"),
                }
            },
        },
    }
    save(OUTPUT / "configuration.json", config)
    print(
        json.dumps(
            {
                "configuration": str(OUTPUT / "configuration.json"),
                "original_native_files_linked": len(linked),
                "reviewed_input_count": len(actual),
                "task_edited": False,
                "publication_done": False,
            }
        )
    )


if __name__ == "__main__":
    main()
