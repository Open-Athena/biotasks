"""Operator release staging from accepted native evidence; never edits task science."""

import json
import subprocess
import sys
from pathlib import Path

from repo2rlenv.campaigns.release import ReleasePlan, ReleaseTask, stage_release, verify_release
from repo2rlenv.emitter.evaluation import EvaluationLabel, evaluation_time
from repo2rlenv.quality.labels import write_labeled_copy

config_path = Path(sys.argv[1])
config = json.loads(config_path.read_text())
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


def read(path):
    return json.loads(Path(path).read_text())


exp = Path("experiments/19-repo2rlenv-notebook-pilot")
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
    "scientific-probes.json": read(grading / "probes.json"),
    "solver-trajectory.json": read(trajectory),
    "source-licenses.json": read(exp / "source-license-evidence.json"),
    "source-intake-provenance.json": read(exp / "seeds/current.json")[0]["provenance"],
    "materialization-manifest.json": read(Path(config["materialization"]) / "manifest.json"),
    "materialization-rationale.json": {
        "rationale": read(Path(config["materialization"]) / "candidate.json")["rationale"]
    },
}
plan = ReleasePlan(
    repo_id="gonzalobenegas/biotasks-notebook-pilot-issue-19",
    recipe="notebook-artifact-reproduction",
    title="BioTasks notebook pilot: marker genes for supplied cell groups",
    description="One notebook-grounded computational biology task: analyze the observed bone-marrow expression matrices using supplied reference-derived cell groups and produce marker-gene statistics. GLM-5.3 authored the task, solution, grader and scientific probes through version-controlled prompts.",
    methodology="BioTasks adapts pinned Repo2RLEnv Tasksmith execution, Harbor packaging and release helpers. The original notebook was executed and replayed. GLM derived identity/group inputs, projected its marker endpoint and wrote an isolated oracle. A fresh worker implemented the public question without answer access. The deterministic grader was tested against original, recomputed and independent outputs, empty/missing submissions and scientific counterexamples. Native Harbor oracle/no-op controls and one blind GLM-5.3 Terminus-2 attempt used CPU-only offline Daytona sandboxes. Reward is binary. Supplied groups are computational reference assignments, not biological ground truth.",
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
    citations=[
        "https://github.com/Open-Athena/biotasks/issues/19",
        "https://github.com/huggingface/Repo2RLEnv/tree/55554430cd724efded1f5ad0ff98ebca5d88c0a6",
        "https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb",
        "https://doi.org/10.6084/m9.figshare.22716739.v1",
    ],
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
