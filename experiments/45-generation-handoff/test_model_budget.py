"""No providers: prove reservations include storage and survive unknown billing."""

import importlib.util
from pathlib import Path

import pytest
from biotasks.validation.files import ValidationError, read_json, sha, write_json

spec = importlib.util.spec_from_file_location(
    "model_budget", Path(__file__).with_name("model_budget.py")
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / "budget.json"
    write_json(
        path,
        {
            "recorded_paid_cost_usd": 0,
            "outstanding_reservations_usd": 10,
            "new_model_calls": 0,
            "paid_model_execution_enabled": False,
            "operating_ceiling_usd": 90,
            "user_limit_exclusive_usd": 100,
            "events": [{"kind": "storage_reservation", "maximum_incremental_usd": 10}],
        },
    )
    return path


def reserve(path, run="reference"):
    return model.reserve(path, run, "13.07", "a" * 64, "b" * 64)


def test_admission_preserves_storage_and_is_idempotent(ledger):
    reserve(ledger)
    before = sha(ledger)
    reserve(ledger)
    assert sha(ledger) == before
    value = read_json(ledger)
    assert value["outstanding_reservations_usd"] == 23.07 and value["new_model_calls"] == 0
    with pytest.raises(ValidationError, match="Changed"):
        model.reserve(ledger, "reference", "13.08", "a" * 64, "b" * 64)


def test_unresolved_runs_are_serial(ledger):
    reserve(ledger)
    before = sha(ledger)
    with pytest.raises(ValidationError, match="serial"):
        reserve(ledger, "other")
    assert sha(ledger) == before


def test_global_ceiling_includes_existing_storage(ledger):
    value = read_json(ledger)
    value["recorded_paid_cost_usd"] = 70
    write_json(ledger, value)
    before = sha(ledger)
    with pytest.raises(ValidationError, match="Cumulative"):
        reserve(ledger)
    assert sha(ledger) == before


def test_complete_billing_releases_only_own_reservation(ledger):
    reserve(ledger)
    row = model.reconcile(ledger, "reference", "0.912345", 6, True, "c" * 64)
    assert row["state"] == "terminal reconciled"
    before = sha(ledger)
    model.reconcile(ledger, "reference", "0.912345", 6, True, "c" * 64)
    assert sha(ledger) == before
    value = read_json(ledger)
    assert (
        value["outstanding_reservations_usd"] == 10 and value["recorded_paid_cost_usd"] == 0.912345
    )
    assert value["new_model_calls"] == 6 and not value["paid_model_execution_enabled"]
    reserve(ledger, "next-reference")


def test_unknown_charge_remains_reserved_and_closes_new_calls(ledger):
    reserve(ledger)
    model.reconcile(ledger, "reference", "0.2", 2, False, "c" * 64)
    value = read_json(ledger)
    assert value["recorded_paid_cost_usd"] == 0.2 and value["outstanding_reservations_usd"] == 22.87
    assert value["model_admission_closed"] and not value["paid_model_execution_enabled"]
    with pytest.raises(ValidationError, match="closed"):
        reserve(ledger, "other")
    with pytest.raises(ValidationError, match="No active"):
        model.verify_reserved(ledger, "reference", "b" * 64)


def test_empty_attempted_evidence_cannot_claim_zero_cost(ledger):
    reserve(ledger)
    model.reconcile(ledger, "reference", "0", None, False, "c" * 64)
    value = read_json(ledger)
    assert value["outstanding_reservations_usd"] == 23.07
    assert not model.rows(value)[0]["call_count_complete"]


def test_approved_final_request_overshoot_is_inside_run_bound(ledger):
    reserve(ledger)
    model.reconcile(ledger, "reference", "7.12", 10, True, "c" * 64)
    value = read_json(ledger)
    assert value["recorded_paid_cost_usd"] == 7.12 and value["outstanding_reservations_usd"] == 10
    assert not value.get("model_admission_closed")


def test_actual_overrun_is_recorded_before_error(ledger):
    reserve(ledger)
    with pytest.raises(model.ModelBudgetExceeded):
        model.reconcile(ledger, "reference", "14", 10, True, "c" * 64)
    value = read_json(ledger)
    assert value["recorded_paid_cost_usd"] == 14 and value["outstanding_reservations_usd"] == 10
    assert value["model_admission_closed"] and not value["paid_model_execution_enabled"]
