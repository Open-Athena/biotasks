import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[3]
SOURCE = "experiments/19-repo2rlenv-notebook-pilot/iris_execution.py"
BASELINE = "afddb9f671ae57412dd0eb3a3292e9cfae3123a8"
spec = importlib.util.spec_from_file_location(
    "solver_window_proof_fixture", HERE / "source_proof.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BEFORE = subprocess.check_output(["git", "show", BASELINE + ":" + SOURCE], cwd=ROOT)
AFTER = (ROOT / SOURCE).read_bytes()


def test_actual_time_admission_only_adds_earlier_refusal():
    module.prove_early_refusal_only(BEFORE, AFTER)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"timeout < self.solver_seconds", b"timeout < 1"),
        (b"math.floor(remaining) - 120", b"math.floor(remaining) + 120"),
        (b'not row.get("cleanup_verified")', b"False"),
        (
            b"self.solver_seconds if solving else None",
            b"min(timeout, self.solver_seconds) if solving else None",
        ),
    ],
)
def test_source_proof_refuses_new_limits_cleanup_bypass_or_shorter_solver(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_early_refusal_only(BEFORE, AFTER.replace(old, new))
