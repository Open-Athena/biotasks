"""Release only excess margin above committed, unchanged lifecycle upper bounds."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
QUESTION_REPAIR_AUDITOR = "e674d133567c5647cf69f9a485a75a91323f49bc212aa82883ab2c49ba1ecab7"
QUESTION_REPAIR_PROFILE = "7ee8d1d97273a2d07d1568599641cd1cb974417a1f7ae8f6cb556ab766b8b0e5"
AUDITORS = {
    "036241de95a1d148af94020839568966c80bb14bba7202c36d73cbc4324cb772",
    # Earlier handled-timeout auditor, before optional observed-clock refinement.
    "25fcbda8ca350cc04434d8c150b25527ae44e868766acfa9be8134184cb50c29",
    "857053031d2eadcf0c22d659d1896ba3c391214eb795f4d8fd3e446483723664",
    QUESTION_REPAIR_AUDITOR,
}


def refinement(proof, row, number):
    assert proof["applied"] is True and proof["helper_sha256"] in AUDITORS
    assert proof.get("observed_clock_refinement", False) is False
    assert proof["actual_invoice_usd"] is None and proof["free_credits_assumed"] is False
    records = [r for r in proof["records"] if r["campaign"] == number]
    assert len(records) == 1
    record = records[0]
    assert row["state"] == "terminal_full_lifecycle_resource_bound_reconciled"
    assert Decimal(row["ceiling_usd"]) == Decimal(record["retained_usd"]) == 2
    if proof["helper_sha256"] == QUESTION_REPAIR_AUDITOR:
        assert proof.get("repair_profile_helper_sha256") == QUESTION_REPAIR_PROFILE
        assert record.get("original_and_fresh_eight_owner_cleanup_verified") is True
    else:
        assert record["original_and_fresh_seven_owner_cleanup_verified"] is True
    assert record["native_auto_snapshot_default"] is False
    assert record["native_snapshot_overrides"] is False
    assert record["conservatively_priced_parallel_sandboxes"] == 2
    assert record["full_approved_lifetime_seconds"] == 7500
    rate = Decimal(record["profile_hourly_usd"])
    bound = Decimal(record["resource_charge_upper_bound_usd"])
    assert bound == 2 * rate * Decimal(7500) / Decimal(3600) == Decimal("1.384500")
    retained = ((bound + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert bound + Decimal("0.10") <= retained < 2
    return record, retained


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, action="append", required=True)
    parser.add_argument("--number", type=int, action="append", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert len(args.previous) == len(args.number) == len(set(args.number))
    assert not args.proof.exists() and args.proof.resolve().is_relative_to(EXPERIMENT)
    ledger_path = EXPERIMENT / "aggregate-budget.json"
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"]) <= 200
    assert Decimal(ledger["ceiling_before_credits"]) == 200
    records = []
    for number, path in zip(args.number, args.previous, strict=True):
        relative = path.resolve().relative_to(EXPERIMENT)
        raw = path.read_bytes()
        assert raw == subprocess.check_output(
            ["git", "show", "HEAD:" + PREFIX + relative.as_posix()], cwd=EXPERIMENT.parents[1]
        )
        row = next(
            r
            for r in ledger["reservations"]
            if r["scope"].startswith(f"autonomous-panel-{number}:")
        )
        assert relative.as_posix() in row["reconciliation"]
        original, retained = refinement(json.loads(raw), row, number)
        row.update(
            ceiling_usd=f"{retained:.2f}",
            state="terminal_verified_full_lifecycle_bound_margin_refined",
            reconciliation=f"Original {relative} remains authoritative: unchanged1.384500USDfull-lifetime bound plus0.10USDminimum margin, rounded upward to0.25USD. No observed-clock discount, repricing, invoice or credits. See "
            + args.proof.resolve().relative_to(EXPERIMENT).as_posix(),
        )
        records.append(
            {
                "campaign": number,
                "prior_proof": relative.as_posix(),
                "prior_proof_sha256": digest(raw),
                "source_manifest_sha256": original["source_manifest_sha256"],
                "unchanged_resource_charge_upper_bound_usd": original[
                    "resource_charge_upper_bound_usd"
                ],
                "prior_hold_usd": "2.00",
                "retained_usd": f"{retained:.2f}",
                "remaining_margin_usd": str(
                    retained - Decimal(original["resource_charge_upper_bound_usd"])
                ),
                "released_usd": f"{Decimal(2) - retained:.2f}",
            }
        )
    after_held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    ledger.update(
        reserved_upper_bound_usd=f"{after_held:.2f}",
        unallocated_usd=f"{200 - after_held:.2f}",
        last_updated_at=datetime.now(UTC).isoformat(),
    )
    ledger["current_summary"] = (
        f"200USD authorized/{after_held:.2f}USD conservative holds/{200 - after_held:.2f}USD unallocated. Reduced only excess margins above unchanged committed complete lifecycle upper bounds; no new funding, invoice or credit assumption."
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "records": records,
        "released_usd": str(held - after_held),
        "aggregate_held_usd": str(after_held),
        "unallocated_usd": str(200 - after_held),
        "no_resource_bound_or_scientific_change": True,
        "new_jobs_or_model_calls": 0,
    }
    args.proof.write_text(json.dumps(result, indent=2) + "\n")
    if args.apply:
        assert ledger_path.read_bytes() == before
        ledger_path.write_bytes(after)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
