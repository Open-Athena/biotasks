"""Serial upstream-call reservations in the existing cumulative epic ledger."""

import math
from decimal import Decimal, InvalidOperation

from biotasks.validation.files import ValidationError, lock, read_json, require, write_json


class ModelBudgetExceeded(ValidationError):
    """Actual cost is recorded; preserve evidence and finish reserved cleanup."""


def create(path, cpu_hours, operating_ceiling, exclusive_limit, storage_reserve):
    """Initialize one shared CPU/model ledger without authorizing execution."""
    require(math.isfinite(cpu_hours) and 0 < cpu_hours <= 1000, "Invalid CPU ceiling")
    operating, limit, storage = map(amount, (operating_ceiling, exclusive_limit, storage_reserve))
    require(0 < operating < limit and storage < operating, "Invalid cumulative paid ceilings")
    with lock(path.with_suffix(path.suffix + ".lock")):
        require(not path.exists(), "Never replace an existing ledger")
        write_json(
            path,
            {
                "schema_version": 1,
                "additional_reserved_cpu_hour_ceiling": cpu_hours,
                "additional_allocated_cpu_hours": 0,
                "outstanding_cpu_hour_reservations": 0,
                "new_paid_capacity_allowed": False,
                "paid_model_execution_enabled": False,
                "admission_closed": False,
                "events": [],
                "recorded_paid_cost_usd": 0,
                "outstanding_reservations_usd": float(storage),
                "new_model_calls": 0,
                "operating_ceiling_usd": float(operating),
                "user_limit_exclusive_usd": float(limit),
            },
        )


def amount(value):
    require(not isinstance(value, bool), "Invalid dollar amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError("Invalid dollar amount") from None
    require(result.is_finite() and result >= 0, "Invalid dollar amount")
    return result


def rows(value):
    return [e for e in value["events"] if e["kind"] == "model_run_reservation"]


def reserve(path, run_id, maximum, quote_sha256, plan_identity):
    maximum = amount(maximum)
    require(
        maximum > 5 and len(quote_sha256) == len(plan_identity) == 64,
        "Missing conservative admission identity",
    )
    with lock(path.with_suffix(path.suffix + ".lock")):
        value = read_json(path)
        existing = next((e for e in rows(value) if e["run_id"] == run_id), None)
        if existing:
            require(
                existing["maximum_usd"] == str(maximum)
                and existing["quote_sha256"] == quote_sha256
                and existing["plan_identity"] == plan_identity,
                "Changed model reservation",
            )
            return existing
        require(not value.get("model_admission_closed"), "Model admission is closed")
        require(
            not any(e["state"] != "terminal reconciled" for e in rows(value)),
            "Another model reservation is unresolved; serial runs only",
        )
        total = (
            amount(value["recorded_paid_cost_usd"])
            + amount(value["outstanding_reservations_usd"])
            + maximum
        )
        require(
            total <= amount(value["operating_ceiling_usd"])
            and total < amount(value["user_limit_exclusive_usd"]),
            "Cumulative model budget cannot reserve this run",
        )
        entry = {
            "kind": "model_run_reservation",
            "run_id": run_id,
            "maximum_usd": str(maximum),
            "outstanding_usd": str(maximum),
            "known_actual_usd": "0",
            "known_calls": 0,
            "call_count_complete": False,
            "state": "reserved before submission",
            "quote_sha256": quote_sha256,
            "plan_identity": plan_identity,
            "model": "openrouter/anthropic/claude-sonnet-4.6",
            "scope": "Only the original upstream bootstrap calls; no repairs/fallback/retries",
            "observations": [],
        }
        value["events"].append(entry)
        value["outstanding_reservations_usd"] = float(
            amount(value["outstanding_reservations_usd"]) + maximum
        )
        value["paid_model_execution_enabled"] = True
        write_json(path, value)
        return entry


def verify_reserved(path, run_id, plan_identity):
    value = read_json(path)
    entry = next(e for e in rows(value) if e["run_id"] == run_id)
    require(
        entry["state"] == "reserved before submission"
        and entry["plan_identity"] == plan_identity
        and not value.get("model_admission_closed"),
        "No active model admission for this source-bound run",
    )
    return entry


def reconcile(path, run_id, known_actual, calls, complete, proof_sha256):
    """Only invoke after source-bound terminal evidence or zero-attempt proof.

    Missing charges retain the entire remaining bound, including requests whose
    outcomes are unknown. No other run is enabled until the hold is resolved.
    """
    known_actual = amount(known_actual)
    require(
        calls is None
        or isinstance(calls, int)
        and not isinstance(calls, bool)
        and 0 <= calls <= 20,
        "Invalid observed upstream request count",
    )
    require(
        isinstance(complete, bool)
        and (not complete or calls is not None)
        and len(proof_sha256) == 64,
        "Missing complete terminal billing identity",
    )
    observation = {
        "known_actual_usd": str(known_actual),
        "known_calls": calls,
        "cost_complete": complete,
        "proof_sha256": proof_sha256,
    }
    problem = None
    with lock(path.with_suffix(path.suffix + ".lock")):
        value = read_json(path)
        entry = next(e for e in rows(value) if e["run_id"] == run_id)
        if entry["observations"] and entry["observations"][-1] == observation:
            return entry
        require(entry["state"] != "terminal reconciled", "Completed model billing changed")
        old_actual, old_outstanding = (
            amount(entry["known_actual_usd"]),
            amount(entry["outstanding_usd"]),
        )
        require(
            known_actual >= old_actual and (calls is None or calls >= entry["known_calls"]),
            "Billing lost previously observed usage",
        )
        maximum = amount(entry["maximum_usd"])
        outstanding = Decimal(0) if complete else max(Decimal(0), maximum - known_actual)
        value["recorded_paid_cost_usd"] = float(
            amount(value["recorded_paid_cost_usd"]) - old_actual + known_actual
        )
        value["outstanding_reservations_usd"] = float(
            amount(value["outstanding_reservations_usd"]) - old_outstanding + outstanding
        )
        value["new_model_calls"] += (calls or 0) - entry["known_calls"] if calls is not None else 0
        entry.update(
            known_actual_usd=str(known_actual),
            outstanding_usd=str(outstanding),
            known_calls=calls if calls is not None else entry["known_calls"],
            call_count_complete=calls is not None,
            state="terminal reconciled" if complete else "billing held",
        )
        entry["observations"].append(observation)
        value["paid_model_execution_enabled"] = False
        if not complete:
            value.update(
                model_admission_closed=True,
                model_admission_closed_reason="Unresolved terminal model billing; retained conservative bound",
            )
        if known_actual > maximum:
            problem = "Model run exceeded its reserved bound"
        elif amount(value["recorded_paid_cost_usd"]) + amount(
            value["outstanding_reservations_usd"]
        ) > amount(value["operating_ceiling_usd"]):
            problem = "Cumulative paid bound exceeded"
        if problem:
            value.update(model_admission_closed=True, model_admission_closed_reason=problem)
        write_json(path, value)
    if problem:
        raise ModelBudgetExceeded(problem)
    return entry
