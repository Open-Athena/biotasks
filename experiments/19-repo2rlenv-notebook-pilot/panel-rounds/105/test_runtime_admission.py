import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "runtime_admission105_fixture", Path(__file__).with_name("runtime_admission.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BEFORE = subprocess.check_output(
    ["git", "show", "25d7703c755e1cfab73f9fe4b4dedb84b7286046:" + module.PREPARE], cwd=ROOT
)
AFTER = (ROOT / module.PREPARE).read_bytes()


def test_actual_source_candidate_and_historical_proofs_are_bound():
    runtime = json.loads(Path(__file__).with_name("candidate-runtime-identity.json").read_text())[
        "runtime_files"
    ]
    result = module.candidate_admission(ROOT, runtime)
    assert result["new_whole_pipeline_live_qualified"] is False
    assert result["new_control_admission_live_verified"] is False
    module.prove_native_writer_only(BEFORE, AFTER)
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(result, module.PREFIX + "grading_session.py", "unreviewed")


@pytest.mark.parametrize(
    "old,new",
    [
        (b"one creation call", b"three creation calls"),
        (b"Do not add scientific computation", b"Add scientific computation"),
        (b"selected stored result's own writer", b"this particular package's writer"),
    ],
)
def test_extra_permission_or_seed_specific_prompt_changes_refused(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_native_writer_only(BEFORE, AFTER.replace(old, new))


def test_unrecorded_resource_source_change_is_not_admitted():
    runtime = json.loads(Path(__file__).with_name("candidate-runtime-identity.json").read_text())[
        "runtime_files"
    ]
    wrong = {**runtime, module.PREFIX + "run_reference_setup.py": "other"}
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, wrong)
