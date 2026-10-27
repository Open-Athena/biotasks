"""Recheck historical source proofs without allowing unknown current workers."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "runtime110_admission", Path(__file__).with_name("runtime_admission.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def runtime():
    return json.loads(Path(__file__).with_name("candidate-runtime-identity.json").read_text())[
        "runtime_files"
    ]


@pytest.fixture(scope="module")
def admitted():
    return module.candidate_admission(ROOT, runtime())


def test_real_frozen_parent_proofs_and_current_reviewed_changes(admitted):
    assert admitted["parent_source_view_cleaned"]
    assert admitted["parent_proofs_rechecked_from_frozen_source"]["revision"] == module.PARENT
    assert len(admitted["reader_predecessor"]) == 235
    assert len(admitted["candidate"]) == 237
    assert admitted["postrun_publication_tests"] == 128
    assert admitted["new_whole_pipeline_live_qualified"] is False


def test_old_provider_proofs_can_bridge_only_explicit_known_source_versions(admitted):
    name = "src/biotasks/prompts/notebook-grader-author.md"
    old = admitted["reader_predecessor"][name]
    assert module.check_source(admitted, name, old) == (
        "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
    )
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(admitted, name, "0" * 64)


@pytest.mark.parametrize(
    "name",
    [
        "src/biotasks/prompts/notebook-task-specification.md",
        "src/biotasks/prompts/notebook-specification-review.md",
        "src/biotasks/prompts/notebook-grader-author.md",
        "experiments/19-repo2rlenv-notebook-pilot/snapshot_archive.py",
        "experiments/19-repo2rlenv-notebook-pilot/release_metadata.py",
        "experiments/19-repo2rlenv-notebook-pilot/run_autonomous.py",
        "experiments/19-repo2rlenv-notebook-pilot/reference_setup.py",
        "experiments/19-repo2rlenv-notebook-pilot/model_profile.py",
    ],
)
def test_unknown_worker_prompt_or_policy_bytes_are_refused(name):
    values = runtime()
    values[name] = "unreviewed"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_runtime_additions_and_removals_are_refused(change):
    values = runtime()
    if change == "missing":
        del values["LICENSE"]
    else:
        values["unknown_worker.py"] = "unreviewed"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)


def test_postrun_change_cannot_weaken_scientific_or_native_completion():
    import subprocess

    name = module.PREFIX + "release_metadata.py"
    before = subprocess.check_output(["git", "show", module.PARENT + ":" + name], cwd=ROOT)
    after = (ROOT / name).read_bytes()
    module.prove_publication_only(before, after)
    changed = after.replace(
        b'pipeline.get("status") != "validated"', b'pipeline.get("status") != "ignored"'
    )
    assert changed != after
    with pytest.raises(AssertionError):
        module.prove_publication_only(before, changed)
