import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "control_admission_proof_fixture", Path(__file__).with_name("control_admission_proof.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NAME = "experiments/19-repo2rlenv-notebook-pilot/grading_session.py"
BEFORE = subprocess.check_output(
    ["git", "show", "25d7703c755e1cfab73f9fe4b4dedb84b7286046:" + NAME], cwd=ROOT
)
AFTER = (ROOT / NAME).read_bytes()


def test_only_two_control_admission_calls_and_one_new_method():
    module.prove_control_admission_only(BEFORE, AFTER)


@pytest.mark.parametrize(
    "old,new",
    [
        (b'report["passed"] == bool(expected_pass)', b"True"),
        (b"set(probe.check_ids) <= failed", b"True"),
        (b'reply.get("probe_valid_execution") is not True', b"False"),
        (b'self.config["verifier_seconds"]', b"999"),
    ],
)
def test_reward_mutation_completion_and_maximum_changes_refused(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_control_admission_only(BEFORE, AFTER.replace(old, new))
