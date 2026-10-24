"""Completion and individual native conditions are separate acceptance claims."""

from typing import Any

import pytest

from biotasks.generation import model_budget, outcomes
from biotasks.validation import budget
from biotasks.validation.files import ValidationError, inventory, read_json


@pytest.mark.parametrize("failed", [None, *outcomes.FLAGS])
def test_profile_requires_all_original_native_conditions(failed):
    result: dict[str, Any] = dict.fromkeys(outcomes.FLAGS, True)
    if failed:
        result[failed] = False
    assert outcomes.profile_eligible(result) is (failed is None)
    if failed:
        del result[failed]
        assert not outcomes.profile_eligible(result)
        result[failed] = 1
        assert not outcomes.profile_eligible(result)


def test_new_ledger_honors_cpu_and_serial_model_admission(tmp_path):
    path = tmp_path / "budget.json"
    model_budget.create(path, 32, 90, 100, 10)
    budget.admit(path, "first", 6, 1 / 6)
    model_budget.reserve(path, "first", "13.07", "a" * 64, "b" * 64)
    with pytest.raises(ValidationError, match="serial runs only"):
        model_budget.reserve(path, "second", "13.07", "a" * 64, "c" * 64)
    value = read_json(path)
    assert value["recorded_paid_cost_usd"] == 0 and value["outstanding_reservations_usd"] == 23.07
    before = inventory(tmp_path)
    with pytest.raises(ValidationError, match="Never replace"):
        model_budget.create(path, 32, 90, 100, 10)
    assert inventory(tmp_path) == before
