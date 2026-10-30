"""Explicit source-family admission, separate from scientific/live qualification."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "source111_admission", Path(__file__).with_name("runtime_admission.py")
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


def test_real_pinned_parent_is_replayed_without_relabeling_new_code(admitted):
    assert admitted["parent_source_view_cleaned"]
    assert admitted["parent_proofs_rechecked_from_frozen_source"]["revision"] == module.PARENT
    assert len(admitted["rollout_review_predecessor"]) == 237
    assert len(admitted["candidate"]) == 242
    assert admitted["offline_review_and_release_checks"] == 175
    assert admitted["new_whole_pipeline_live_qualified"] is False
    assert admitted["new_source_funding_typed_pool_and_cleanup_checks_still_required"]


def test_previous_source_family_is_an_explicit_delta_only(admitted):
    path = "src/biotasks/prompts/notebook-task-specification.md"
    old = admitted["rollout_review_predecessor"][path]
    assert (
        module.check_source(admitted, path, old)
        == "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
    )
    unchanged = "experiments/19-repo2rlenv-notebook-pilot/model_profile.py"
    assert (
        module.check_source(admitted, unchanged, admitted["candidate"][unchanged])
        == "exact_previous_proof_bytes"
    )
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(admitted, path, "0" * 64)


@pytest.mark.parametrize(
    "path",
    [
        "src/biotasks/chat_author.py",
        "src/biotasks/prompts/notebook-native-review.md",
        "experiments/19-repo2rlenv-notebook-pilot/native_review.py",
        "experiments/19-repo2rlenv-notebook-pilot/run_autonomous.py",
        "experiments/19-repo2rlenv-notebook-pilot/release_metadata.py",
        "experiments/19-repo2rlenv-notebook-pilot/model_profile.py",
        "experiments/19-repo2rlenv-notebook-pilot/iris_execution.py",
    ],
)
def test_unknown_prompt_worker_model_transport_or_release_bytes_are_refused(path):
    values = runtime()
    values[path] = "unreviewed"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_missing_review_or_unreviewed_extra_module_cannot_be_admitted(change):
    values = runtime()
    if change == "missing":
        values.pop("experiments/19-repo2rlenv-notebook-pilot/native_review.py")
    else:
        values["unreviewed-worker.py"] = "unreviewed"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, values)
