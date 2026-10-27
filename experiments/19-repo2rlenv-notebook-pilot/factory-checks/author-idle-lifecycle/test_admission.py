"""The lifecycle bridge must reject changed hard limits or scientific behavior."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[2] / "panel-rounds/102/runtime_admission.py"
spec = importlib.util.spec_from_file_location("idle_admission", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BEFORE = (
    "create(parameters(auto_stop_interval=30, ttl_minutes=125, cpu=4)); compute(method='original')"
)
AFTER = BEFORE.replace("auto_stop_interval=30", "auto_stop_interval=0")


def test_only_idle_expiry_is_disabled():
    module.prove_idle_only(BEFORE, AFTER)


@pytest.mark.parametrize(
    "altered",
    [
        AFTER.replace("ttl_minutes=125", "ttl_minutes=0"),
        AFTER.replace("ttl_minutes=125", "ttl_minutes=126"),
        AFTER.replace("cpu=4", "cpu=8"),
        AFTER.replace("method='original'", "method='different'"),
        AFTER.replace("auto_stop_interval=0", "auto_stop_interval=1"),
        AFTER + "; delete_unrelated()",
    ],
)
def test_other_runtime_changes_remain_rejected(altered):
    with pytest.raises(AssertionError):
        module.prove_idle_only(BEFORE, altered)


def test_unknown_earlier_proof_source_is_not_bridged():
    admission = {
        "old": {"file": "older"},
        "predecessor": {"file": "base"},
        "candidate": {"file": "new"},
        "allowed_source_deltas": {"file": "new"},
    }
    assert module.check_source(admission, "file", "base").startswith("explicit_tested")
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(admission, "file", "unreviewed")
