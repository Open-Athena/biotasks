"""Atomic cumulative reserved-CPU admissions, including cleanup before submission."""

import math
from pathlib import Path
from typing import Any

from biotasks.validation.files import ValidationError, lock, read_json, require, write_json


class BudgetExceeded(ValidationError):
    """Actual CPU is recorded; no new primary work, but finish preservation/cleanup."""


def create(path: Path, ceiling: float) -> None:
    require(math.isfinite(ceiling) and 0 < ceiling <= 1000, "Invalid CPU ceiling")
    with lock(path.with_suffix(path.suffix + ".lock")):
        require(not path.exists(), "Never replace an existing ledger")
        write_json(
            path,
            {
                "schema_version": 1,
                "additional_reserved_cpu_hour_ceiling": ceiling,
                "additional_allocated_cpu_hours": 0,
                "outstanding_cpu_hour_reservations": 0,
                "new_paid_capacity_allowed": False,
                "paid_model_execution_enabled": False,
                "admission_closed": False,
                "events": [],
            },
        )


def totals(value: dict[str, Any]) -> None:
    events = [e for e in value["events"] if e["kind"] == "reserved_cpu_admission"]
    value["additional_allocated_cpu_hours"] = sum(
        e["actual_allocated_cpu_hours"] for e in events if e["state"] == "terminal reconciled"
    )
    value["outstanding_cpu_hour_reservations"] = sum(
        e["maximum_allocated_cpu_hours"]
        for e in events
        if e["state"] == "reserved before submission"
    )


def admit(path: Path, run_id: str, maximum: float, cleanup: float) -> dict[str, Any]:
    require(all(math.isfinite(v) and v > 0 for v in (maximum, cleanup)), "Invalid CPU bound")
    with lock(path.with_suffix(path.suffix + ".lock")):
        value = read_json(path)
        require(not value.get("admission_closed"), "CPU admission is closed")
        require(value["new_paid_capacity_allowed"] is False, "This backend cannot create capacity")
        require(value["paid_model_execution_enabled"] is False, "Validation cannot call models")
        totals(value)
        names = [(run_id, maximum), (run_id + "-stop", cleanup), (run_id + "-cleanup", cleanup)]
        existing = {
            e.get("run_id"): e for e in value["events"] if e["kind"] == "reserved_cpu_admission"
        }
        if any(name in existing for name, _ in names):
            require(
                all(
                    name in existing and existing[name]["maximum_allocated_cpu_hours"] == bound
                    for name, bound in names
                ),
                "Changed or incomplete admission",
            )
        else:
            bound = (
                value["additional_allocated_cpu_hours"]
                + value["outstanding_cpu_hour_reservations"]
                + maximum
                + 2 * cleanup
            )
            require(bound <= value["additional_reserved_cpu_hour_ceiling"], "CPU ceiling exceeded")
            for name, amount in names:
                value["events"].append(
                    {
                        "kind": "reserved_cpu_admission",
                        "run_id": name,
                        "maximum_allocated_cpu_hours": amount,
                        "new_paid_capacity": False,
                        "state": "reserved before submission",
                        "controller": "biotasks.validation.v1",
                        "role": "primary" if name == run_id else name.rsplit("-", 1)[-1],
                    }
                )
            totals(value)
            write_json(path, value)
        return {
            "run_id": run_id,
            "maximum_cpu_hours": maximum,
            "cleanup_cpu_hours": cleanup,
            "admitted_before_submission": True,
            "model_calls": 0,
            "new_capacity": False,
        }


def verify_reserved(path: Path, run_id: str) -> None:
    value = read_json(path)
    event = next(e for e in value["events"] if e.get("run_id") == run_id)
    require(event["state"] == "reserved before submission", "Run has no outstanding admission")
    role = event.get("role", run_id.rsplit("-", 1)[-1])
    require(
        not value.get("admission_closed") or role in ("cleanup", "stop"),
        "CPU admission is closed; only already reserved stop/cleanup may start",
    )


def reconcile(path: Path, run_id: str, actual: float) -> None:
    require(math.isfinite(actual) and actual >= 0, "Invalid actual CPU allocation")
    with lock(path.with_suffix(path.suffix + ".lock")):
        value = read_json(path)
        event = next(e for e in value["events"] if e.get("run_id") == run_id)
        if event["state"] == "terminal reconciled":
            require(event["actual_allocated_cpu_hours"] == actual, "Accounting changed")
        else:
            require(event["state"] == "reserved before submission", "Admission is not reserved")
            event.update(state="terminal reconciled", actual_allocated_cpu_hours=actual)
        totals(value)
        problem = None
        if actual > event["maximum_allocated_cpu_hours"]:
            problem = "Actual CPU bound exceeded"
        elif (
            value["additional_allocated_cpu_hours"] + value["outstanding_cpu_hour_reservations"]
            > value["additional_reserved_cpu_hour_ceiling"]
        ):
            problem = "Cumulative CPU ceiling exceeded"
        if problem:
            value.update(admission_closed=True, admission_closed_reason=problem)
        # Preserve actual overspend before reporting it; never hide failed attempts.
        write_json(path, value)
        if problem:
            raise BudgetExceeded(problem)


def release_cleanup(path: Path, run_id: str, proof: dict[str, Any], role: str = "cleanup") -> None:
    require(proof.get("verified_empty") or proof.get("verified_no_creation"), "No cleanup proof")
    with lock(path.with_suffix(path.suffix + ".lock")):
        value = read_json(path)
        require(role in ("cleanup", "stop"), "Unknown reservation role")
        event = next(e for e in value["events"] if e.get("run_id") == run_id + "-" + role)
        require(
            event["state"] in ("reserved before submission", "released unused"), "Cleanup spent"
        )
        event.update(state="released unused", reason="Verified empty/no-creation; no cleanup job")
        totals(value)
        write_json(path, value)
