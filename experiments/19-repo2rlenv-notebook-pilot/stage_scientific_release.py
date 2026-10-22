"""Operator release staging from accepted native evidence; never edits task science."""

import json
import subprocess
import sys
from pathlib import Path

from release_metadata import (
    load_release_metadata,
    scientific_probe_documents,
    verify_bundle_licenses,
)
from repo2rlenv.campaigns.release import ReleasePlan, ReleaseTask, stage_release, verify_release
from repo2rlenv.emitter.evaluation import EvaluationLabel, evaluation_time
from repo2rlenv.quality.labels import write_labeled_copy

config_path = Path(sys.argv[1])
config = json.loads(config_path.read_text())
metadata, licenses, provenance = load_release_metadata(config)
native, task, grading, stage = map(
    Path, [config[k] for k in ("native", "task", "grading", "stage")]
)
assert not stage.exists()
checked = subprocess.run(
    [
        sys.executable,
        str(Path(__file__).with_name("check_scientific_release.py")),
        str(native),
        str(task),
        str(grading),
    ],
    capture_output=True,
    text=True,
    check=True,
)
validation = json.loads(checked.stdout)
assert validation["accepted"] is True
verify_bundle_licenses(task, licenses)


def read(path):
    return json.loads(Path(path).read_text())


# Upstream's verified label specifically requires its standard quality-loop proof.
# Preserve that distinction rather than fabricating compatible trial records.
labeled = write_labeled_copy(
    task,
    Path(config["labeled"]) / task.name,
    EvaluationLabel(
        status="unverified",
        stage="complete",
        provenance="assisted",
        reason_codes=["upstream_quality_loop_not_run"],
        checked_at=evaluation_time(),
        profile="biotasks-scientific-content-v1",
        subject_bundle_hash=validation["bundle_hash"],
        detail="BioTasks scientific-content controls and native Harbor controls passed; a blind GLM attempt was recorded. These checks use the BioTasks artifact workflow, not the standard upstream quality-loop acceptance profile. See the release validation evidence.",
    ),
)
raw_summary = read(native / "result.json")
trajectory = native / raw_summary["solver"]["result_path"]
trajectory = trajectory.parent / "agent/trajectory.json"
assert trajectory.is_file()
documents = {
    "validation-summary.json": validation,
    "grading-result.json": read(grading / "result.json"),
    "grading-controls.json": {"controls": read(grading / "final-controls.json")},
    "grading-rationale.json": {"rationale": read(grading / "final-candidate.json")["rationale"]},
    "grading-review.json": read(
        grading
        / ("review-repair.json" if (grading / "review-repair.json").exists() else "review.json")
    ),
    "independent-solution.json": read(grading / "independent-solution.json"),
    "independent-execution.json": read(grading / "independent-result.json"),
    **scientific_probe_documents(grading),
    "solver-trajectory.json": read(trajectory),
    "source-licenses.json": licenses,
    "source-intake-provenance.json": provenance,
    "materialization-manifest.json": read(Path(config["materialization"]) / "manifest.json"),
    "materialization-rationale.json": {
        "rationale": read(Path(config["materialization"]) / "candidate.json")["rationale"]
    },
}
plan = ReleasePlan(
    repo_id=metadata["repo_id"],
    recipe="notebook-artifact-reproduction",
    title=metadata["title"],
    description=metadata["description"],
    methodology=metadata["methodology"],
    code_revision=config["revision"],
    tasks=[
        ReleaseTask(
            path=labeled,
            bundle_hash=validation["bundle_hash"],
            evidence={
                "scientific_content_controls_passed": True,
                "native_trials": validation["native_trials"],
                "standard_upstream_quality_loop_run": False,
            },
            evidence_documents=documents,
        )
    ],
    economics={
        "model": "glm-5.3",
        "solver_seconds_limit": 600,
        "cpu": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "actual_daytona_invoice_usd": None,
        "aggregate_authorized_usd": "100.00",
    },
    citations=metadata["citations"],
    limitations=[
        "One task and one final blind attempt do not establish benchmark performance or universal software portability.",
        "The upstream advisory evaluation label remains unverified because its standard quality-loop profile was not run. The separate, executed BioTasks scientific-content and native-control evidence is provided explicitly.",
        "All authoring, validation implementation and solver workers used GLM-5.3; separation of inputs does not imply independence of model families.",
        "The frozen reference and inputs ground this computational reproduction task; successful execution and numerical agreement do not establish biological validity.",
        "The Python dependency lock is preserved. Base-image tags and system-package repositories are not immutable rebuild guarantees.",
        "The source notebook and reference-derived answers are public, so this is not a hidden contamination-free benchmark.",
    ],
)
plan_path = Path(config["plan"])
plan_path.write_text(plan.model_dump_json(indent=2) + "\n")
manifest = stage_release(plan, stage)
verify_release(stage)
print(
    json.dumps(
        {
            "staged": str(stage),
            "bundle_hash": validation["bundle_hash"],
            "task_count": manifest["task_count"],
            "plan": str(plan_path),
        }
    )
)
