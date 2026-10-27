"""Prepare release metadata for an accepted bundle with exact reviewed input bytes.

Publication bookkeeping only: do not edit task science, licenses or original seals.
Input filenames may differ; content identities and their notice context must match.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
BASE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2) + "\n")


def reviewed_input_mapping(inputs, prior):
    expected = {(row["sha256"], row["bytes"]): row for row in prior["inputs"]}
    assert expected and len(expected) == len(prior["inputs"])
    actual, seen = [], set()
    for path in sorted(inputs.rglob("*")):
        assert not path.is_symlink()
        if path.is_dir():
            continue
        assert path.is_file()
        identity = digest(path), path.stat().st_size
        row = expected[identity]
        seen.add(identity)
        actual.append(
            {
                "path": path.relative_to(inputs).as_posix(),
                "reviewed_original_path": row["path"],
                "bytes": identity[1],
                "sha256": identity[0],
                "source_url": row["source_url"],
            }
        )
    assert seen == set(expected)
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--notice-review", type=Path, required=True)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--runtime-revision", required=True)
    args = parser.parse_args()
    archive = BASE / f"archives/{args.number:03}"
    files, output = archive / "files", BASE / f"release{args.number:03}"
    assert not output.exists()
    readback = read(archive / "independent-readback.json")
    assert readback["all_files_download_verified"]
    assert digest(archive / "sealed-manifest.json") == readback["source_manifest_sha256"]
    assert read(archive / "root-evidence/readback.json")[
        "all_manifest_files_hash_size_mode_verified"
    ]
    cleanup = read(archive / "fresh-provider-cleanup.json")
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["fresh_original_ids_absent"] and not cleanup["sandboxes"]
    pipeline = read(files / "pipeline.json")
    assert pipeline["status"] == "validated" and pipeline["operator_interventions"] == 0
    payload = BASE / f"launch/{args.number:03}-payload"
    seeds = read(payload / "seeds.json")
    assert seeds == [pipeline["source"]]
    assert read(files / "intake/conversion.json")["source_sha256"] == seeds[0]["source_sha256"]
    assert Path(pipeline["effective_grading"]).name == "grading"
    assert Path(pipeline["effective_materialization"]).name == "materialization"
    task = files / f"native/tasks/autonomous-panel-{args.number:03}"
    checked = subprocess.run(
        [
            sys.executable,
            str(EXPERIMENT / "check_scientific_release.py"),
            str(files / "native"),
            str(task),
            str(files / "grading"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    qualification = json.loads(checked.stdout)
    assert qualification["accepted"]
    notices = read(task / "environment/SOURCE-LICENSES.json")
    prior = read(args.notice_review)
    assert notices["notebook_source_sha256"] == prior["notebook_source_sha256"]
    primary = {row["name"]: row for row in prior["primary_sources"]}
    assert primary["notebook-license"]["sha256"] == notices["notebook_license"]["sha256"]
    assert (
        hashlib.sha256(notices["notebook_license"]["text"].encode()).hexdigest()
        == (notices["notebook_license"]["sha256"])
    )
    for source in notices["data_license"]["sources"]:
        assert source["distribution_license_sha256"] == primary["testsuite-license"]["sha256"]
        assert source["package_readme_sha256"] == primary["testsuite-readme"]["sha256"]
        assert (
            hashlib.sha256(source["distribution_license_text"].encode()).hexdigest()
            == (source["distribution_license_sha256"])
        )
    assert "pinned-data-policy" in primary
    actual = reviewed_input_mapping(task / "environment/inputs", prior)
    output.mkdir(mode=0o700)
    save(output / "qualification.json", qualification)
    rights = {
        **prior,
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": "Fresh exact native input bytes and unchanged notice context; filenames may differ.",
        "inputs": actual,
        "prior_input_notice_review_sha256": digest(args.notice_review),
        "current_notebook_license_and_distribution_texts_verified": True,
        "input_origin": notices["source_provenance"].get("data_lineage"),
        "task_bundle_edited": False,
        "new_models_hosts_sandboxes": 0,
    }
    save(output / "input-notice-review.json", rights)
    view = output / "original-export-view"
    view.mkdir()
    raw_manifest = (archive / "sealed-manifest.json").read_bytes()
    (view / "export-manifest.json").write_bytes(raw_manifest)
    for row in json.loads(raw_manifest)["files"]:
        name = row["path"]
        if name != "pipeline.json" and not name.startswith("native/"):
            continue
        source = files / name
        assert not source.is_symlink() and source.is_file()
        assert source.stat().st_size == row["bytes"] and digest(source) == row["sha256"]
        assert source.stat().st_mode & 0o777 == row["mode"]
        destination = view / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)
    native = read(files / "native/result.json")
    rewards = [str(item["reward"]) for item in [*native["controls"], native["solver"]]]
    config = {
        "revision": args.runtime_revision,
        "release_stager_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=EXPERIMENT.parents[1], text=True
        ).strip(),
        "native": str(view / "native"),
        "task": str(task),
        "grading": str(files / "grading"),
        "materialization": str(files / "materialization"),
        "stage": str(output / "staged"),
        "labeled": str(output / "labeled"),
        "plan": str(output / "release-plan.json"),
        "autonomous_pipeline": str(view / "pipeline.json"),
        "autonomous_archive_manifest": str(view / "export-manifest.json"),
        "aggregate_authorized_usd": "200.00",
        "release_metadata": {
            "repo_id": args.repo_id,
            "title": seeds[0].get("title", "Notebook-grounded computational biology task"),
            "description": "One computational biology task preserving the original notebook's inputs and methods, with executed scientific controls and a blind solver attempt.",
            "methodology": (
                "The autonomous factory received only the pinned notebook and provenance. "
                "GLM-5.3 authored the exports, setup, task and executable comparisons; no operator scientific edits. "
                f"The exact final suite contains {qualification['scientific_controls']} controls; native reference/empty/blind-GLM rewards are {'/'.join(rewards)}. "
                "Native high effort was requested; effective served effort is unverified. "
                "Qualification follows BioTasks scientific/native gates, not the standard upstream quality-loop profile. "
                "The exact input bytes and unchanged full notices match the separate source-specific review. "
                "No blanket relicense, commercial-training grant, biological-validity or universal portability claim is inferred."
            ),
            "licenses_file": str(task / "environment/SOURCE-LICENSES.json"),
            "seed_file": str(payload / "seeds.json"),
            "citations": [
                seeds[0]["url"],
                *[r["url"] for r in prior["primary_sources"]],
                "https://github.com/Open-Athena/biotasks/issues/19",
            ],
            "evidence_documents": {
                name: {"path": str(output / name), "sha256": digest(output / name)}
                for name in ("input-notice-review.json", "qualification.json")
            },
        },
    }
    save(output / "configuration.json", config)
    print(
        json.dumps(
            {
                "configuration": str(output / "configuration.json"),
                "input_identities_verified": len(actual),
                "task_edited": False,
                "publication_done": False,
            }
        )
    )


if __name__ == "__main__":
    main()
