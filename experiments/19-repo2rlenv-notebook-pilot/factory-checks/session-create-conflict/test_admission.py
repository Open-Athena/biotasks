"""Source admission preserves the single execute and existing hard deadlines."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
path = EXPERIMENT / "panel-rounds/103/runtime_admission.py"
spec = importlib.util.spec_from_file_location("creation_admission", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BEFORE = subprocess.check_output(
    ["git", "show", module.BASE + ":" + module.PREFIX + "daytona_session.py"], cwd=ROOT
)
AFTER = (EXPERIMENT / "daytona_session.py").read_bytes()


def test_known_creation_delta_only():
    module.prove_creation_only(BEFORE, AFTER)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"creation == 1", b"creation >= 0"),
        (b"existing.commands != []", b"False"),
        (b"existing.session_id != session", b"False"),
        (b"submission_attempts=1", b"submission_attempts=2"),
        (b"deadline = time.monotonic() + timeout", b"deadline = time.monotonic() + timeout + 10"),
        (b"range(2)", b"range(3)"),
    ],
)
def test_execution_identity_and_budget_changes_are_not_admitted(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_creation_only(BEFORE, AFTER.replace(old, new))


def test_unknown_source_family_refused():
    value = {
        "old": {"file": "older"},
        "predecessor": {"file": "base"},
        "lifecycle_predecessor": {"file": "idle"},
        "candidate": {"file": "new"},
        "allowed_source_deltas": {"file": "new"},
    }
    assert module.check_source(value, "file", "idle").startswith("explicit_tested")
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(value, "file", "unreviewed")
