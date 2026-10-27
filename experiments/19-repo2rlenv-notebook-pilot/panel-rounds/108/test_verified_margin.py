import importlib.util
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "verified_margin", Path(__file__).with_name("refine_verified_margin.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PROOFS = [
    (151, "043/cross-domain-resource-reconciliation.json"),
    (176, "080/completed-176-applied.json"),
    (198, "101/closed-198-native-applied.json"),
    (215, "108/closed-215-native-applied.json"),
]


def evidence(number=215, name="108/closed-215-native-applied.json"):
    proof = json.loads((module.EXPERIMENT / "panel-rounds" / name).read_text())
    row = {"ceiling_usd": "2.00", "state": "terminal_full_lifecycle_resource_bound_reconciled"}
    return proof, row, number


@pytest.mark.parametrize("number,name", PROOFS)
def test_real_strict_proofs_keep_the_entire_original_bound_plus_margin(number, name):
    proof, row, number = evidence(number, name)
    before = deepcopy((proof, row))
    original, retained = module.refinement(proof, row, number)
    assert retained == Decimal("1.50")
    assert retained - Decimal(original["resource_charge_upper_bound_usd"]) == Decimal("0.115500")
    assert (proof, row) == before


@pytest.mark.parametrize(
    "defect",
    [
        "dry_run",
        "unrecognized_auditor",
        "clock_discount",
        "invoice",
        "credits",
        "already_refined",
        "lower_hold",
        "no_cleanup",
        "snapshot",
        "extra_concurrency",
        "shortened_lifetime",
        "changed_rate",
        "lower_bound",
        "duplicate_campaign",
        "wrong_campaign",
    ],
)
def test_unproved_or_already_applied_margin_cannot_be_released(defect):
    proof, row, number = evidence()
    record = proof["records"][0]
    if defect == "dry_run":
        proof["applied"] = False
    elif defect == "unrecognized_auditor":
        proof["helper_sha256"] = "unknown"
    elif defect == "clock_discount":
        proof["observed_clock_refinement"] = True
    elif defect == "invoice":
        proof["actual_invoice_usd"] = "0.01"
    elif defect == "credits":
        proof["free_credits_assumed"] = True
    elif defect == "already_refined":
        row["state"] = "terminal_verified_full_lifecycle_bound_margin_refined"
    elif defect == "lower_hold":
        row["ceiling_usd"] = "1.50"
    elif defect == "no_cleanup":
        record["original_and_fresh_seven_owner_cleanup_verified"] = False
    elif defect == "snapshot":
        record["native_snapshot_overrides"] = True
    elif defect == "extra_concurrency":
        record["conservatively_priced_parallel_sandboxes"] = 3
    elif defect == "shortened_lifetime":
        record["full_approved_lifetime_seconds"] = 6000
    elif defect == "changed_rate":
        record["profile_hourly_usd"] = "0.1"
    elif defect == "lower_bound":
        record["resource_charge_upper_bound_usd"] = "0.5"
    elif defect == "duplicate_campaign":
        proof["records"].append(deepcopy(record))
    else:
        number = 999
    with pytest.raises(AssertionError):
        module.refinement(proof, row, number)
