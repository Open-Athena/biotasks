import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "runtime_admission107_fixture", Path(__file__).with_name("runtime_admission.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def runtime():
    return json.loads(Path(__file__).with_name("candidate-runtime-identity.json").read_text())[
        "runtime_files"
    ]


def test_actual_diagnostic_candidate_retains_prior_provider_gates_and_no_live_claim():
    result = module.candidate_admission(ROOT, runtime())
    assert result["new_citation_feedback_live_verified"] is False
    assert result["new_whole_pipeline_live_qualified"] is False
    name = module.PREFIX + "specification_protocol.py"
    assert module.check_source(result, name, result["feedback_predecessor"][name]) == (
        "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
    )
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(result, name, "unreviewed")


@pytest.mark.parametrize(
    "path", ["run_reference_setup.py", "specification_protocol.py", "grading_session.py"]
)
def test_unknown_creator_predicate_or_grader_bytes_cannot_enter_this_candidate(path):
    wrong = {**runtime(), module.PREFIX + path: "unrecorded"}
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, wrong)
