"""Source admission preserves parent proofs and refuses unknown worker bytes."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "runtime109_admission", Path(__file__).with_name("runtime_admission.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def runtime():
    return json.loads(
        (EXPERIMENT / "factory-checks/table-parsing/candidate-runtime-identity.json").read_text()
    )["runtime_files"]


def test_actual_parent_proofs_and_explicit_candidate_checks():
    result = module.candidate_admission(ROOT, runtime())
    assert result["parent_source_view_cleaned"]
    assert result["parent_proofs_rechecked_from_frozen_source"]["revision"] == module.PARENT
    assert len(result["common_predecessor"]) == 232
    assert len(result["candidate"]) == 235
    assert result["new_shared_reader_live_verified"] is False
    assert result["new_primary_snapshot_live_verified"] is False
    assert result["new_whole_pipeline_live_qualified"] is False
    name = module.PREFIX + "iris_bootstrap.py"
    assert module.check_source(result, name, result["common_predecessor"][name]) == (
        "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
    )
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(result, name, "unreviewed")


@pytest.mark.parametrize(
    "name",
    [
        "iris_bootstrap.py",
        "run_autonomous.py",
        "reference_setup.py",
        "grading_session.py",
        "scientific_bundle.py",
        "model_profile.py",
        "grader_support.py",
    ],
)
def test_changed_worker_or_policy_cannot_use_recorded_admission(name):
    values = {**runtime(), module.PREFIX + name: "not-the-recorded-source"}
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)


@pytest.mark.parametrize("change", ["missing", "extra", "reader"])
def test_runtime_removal_addition_or_unrecorded_reader_is_refused(change):
    values = runtime()
    if change == "missing":
        del values["LICENSE"]
    elif change == "extra":
        values[module.PREFIX + "unknown_worker.py"] = "unreviewed"
    else:
        values["src/biotasks/table_io.py"] = "unreviewed"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)
