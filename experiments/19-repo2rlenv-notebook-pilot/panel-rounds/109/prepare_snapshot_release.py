"""Stage publication metadata from an original primary snapshot and input review.

No task edits, scientific execution, new resource allocation or upload occurs.
The source-specific rights decision must already exist as a reviewed document.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
from snapshot_archive import verify_snapshot_archive  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--notice-review", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--repo-id", required=True)
    args = parser.parse_args()
    archive = args.private_root / f"archives/{args.number:03}"
    payload = args.private_root / f"launch/{args.number:03}-payload"
    output = args.private_root / f"release{args.number:03}"
    assert not output.exists()
    snapshot_config = {
        "restored": str(archive / "snapshot-restored"),
        "transport": str(archive / "snapshot-transport"),
        # Retain the original download tool's historical receipt filename.
        "recovery": str(archive / "failure-archive-readback.json"),
        "claim": str(args.private_root / f"launch/{args.number:03}-submission.json"),
        "bootstrap": str(payload / "bootstrap.py"),
    }
    snapshot = verify_snapshot_archive(**snapshot_config)
    files = snapshot.root
    pipeline = snapshot.read_json("pipeline.json")
    assert pipeline["status"] == "validated" and pipeline["operator_interventions"] == 0
    freeze = read(args.freeze)
    claim = read(Path(snapshot_config["claim"]))
    assert freeze["input_revision"] == pipeline["factory_revision"] == claim["factory_revision"]
    assert freeze["payload_files"] == claim["inputs"]["files"]
    bootstrap = read(archive / "root-evidence/files/bootstrap-status.json")
    assert bootstrap["completed"] is True and not bootstrap.get("error_type")
    cleanup = read(archive / "fresh-provider-cleanup.json")
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["fresh_original_ids_absent"] and not cleanup["sandboxes"]
    assert cleanup["source_snapshot_manifest_sha256"] == snapshot.evidence["member_manifest_sha256"]
    assert (
        cleanup["source_transport_manifest_sha256"]
        == snapshot.evidence["transport_manifest_sha256"]
    )
    seeds = read(payload / "seeds.json")
    assert seeds == [pipeline["source"]]
    task = files / f"native/tasks/autonomous-panel-{args.number:03}"
    notices = read(task / "environment/SOURCE-LICENSES.json")
    reviewed = read(args.notice_review)
    assert reviewed["task_science_or_native_bundle_edited"] is False
    assert reviewed["source_notices_sha256"] == digest(task / "environment/SOURCE-LICENSES.json")
    assert reviewed["notebook_source_sha256"] == seeds[0]["source_sha256"]
    expected = {(r["sha256"], r["bytes"]): r for r in reviewed["inputs"]}
    assert expected and len(expected) == len(reviewed["inputs"])
    actual = set()
    for path in (task / "environment/inputs").rglob("*"):
        assert not path.is_symlink()
        if path.is_dir():
            continue
        identity = digest(path), path.stat().st_size
        assert identity in expected
        actual.add(identity)
    assert actual == set(expected)
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
    assert qualification["accepted"] is True
    native = snapshot.read_json("native/result.json")
    rewards = [r["reward"] for r in [*native["controls"], native["solver"]]]
    output.mkdir(mode=0o700)
    save(output / "qualification.json", qualification)
    save(output / "input-notice-review.json", reviewed)
    save(
        output / "primary-snapshot-verification.json",
        {
            **snapshot.evidence,
            "archive_role": "primary",
            "bootstrap_completed": True,
            "historical_recovery_receipt_filename_does_not_imply_host_failure": True,
            "fresh_provider_cleanup_verified": True,
        },
    )
    evidence_names = (
        "input-notice-review.json",
        "qualification.json",
        "primary-snapshot-verification.json",
    )
    config = {
        # Public source revision for navigation; private source/input revision
        # remains unchanged in the original autonomous execution evidence.
        "revision": freeze["public_runtime_revision"],
        "release_stager_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=EXPERIMENT.parents[1], text=True
        ).strip(),
        "native": str(files / "native"),
        "task": str(task),
        "grading": str(files / "grading"),
        "materialization": str(files / "materialization"),
        "stage": str(output / "staged"),
        "labeled": str(output / "labeled"),
        "plan": str(output / "release-plan.json"),
        "autonomous_pipeline": str(files / "pipeline.json"),
        "autonomous_snapshot": snapshot_config,
        "aggregate_authorized_usd": "200.00",
        "release_metadata": {
            "repo_id": args.repo_id,
            "title": seeds[0].get("title", "Notebook-grounded computational biology task"),
            "description": "One notebook-grounded computational biology task with executed scientific controls and a blind solver attempt.",
            "methodology": (
                "The factory received only the original pinned notebook and provenance. GLM-5.3 authored exports, setup, task and executable comparisons, without operator scientific edits. "
                f"The final suite has {qualification['scientific_controls']} controls; native reference/empty/blind-GLM rewards are {rewards}. "
                "Native high was requested; effective served effort is unverified. "
                "The original primary compressed snapshot and its member/transport identities are independently verified. No normal per-file seal was reconstructed. "
                "Scientific/native qualification uses the BioTasks profile, not upstream standard quality-loop approval. Source-specific input notices and historical pending-review metadata are retained."
            ),
            "licenses_file": str(task / "environment/SOURCE-LICENSES.json"),
            "seed_file": str(payload / "seeds.json"),
            "citations": [
                seeds[0]["url"],
                *[r["url"] for r in reviewed["primary_sources"]],
                "https://github.com/Open-Athena/biotasks/issues/19",
            ],
            "evidence_documents": {
                name: {"path": str(output / name), "sha256": digest(output / name)}
                for name in evidence_names
            },
        },
    }
    assert notices["notebook_source_sha256"] == reviewed["notebook_source_sha256"]
    save(output / "configuration.json", config)
    print(
        json.dumps(
            {
                "campaign": args.number,
                "configured": True,
                "task_edited": False,
                "native_rewards": rewards,
                "primary_archive_verified": True,
                "publication_done": False,
            }
        )
    )


if __name__ == "__main__":
    main()
