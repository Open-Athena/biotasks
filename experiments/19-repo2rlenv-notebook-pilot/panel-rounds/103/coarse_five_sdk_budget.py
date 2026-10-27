"""Keep a conservative full-lifetime hold for a verified five-SDK failure.

Operator accounting only. Every sandbox is charged for125minutes plus300seconds
at EACH end, regardless of observed overlap or shorter execution. No native
trial, uncertain creation, unknown source or incomplete cleanup is admitted.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/070"))
from closed_session_bound import RATE, closed_session_bound  # noqa: E402

FOLDERS = {"setup-raw", "replay", "materialization-raw", "grading", "grading-comparison-repair"}


def full_profile(sessions, pipeline):
    assert set(sessions) == FOLDERS
    records = {
        name: closed_session_bound(session, pipeline, [], 300) for name, session in sessions.items()
    }
    # Full125minute lifetime plus margins covers every actual original clock.
    per_box = Decimal(8100) * RATE / 3600
    assert all(
        Decimal(row["priced_seconds"]) <= 8100
        and Decimal(row["resource_upper_bound_usd"]) <= per_box
        for row in records.values()
    )
    full = per_box * len(FOLDERS)
    retained = ((full + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert retained == Decimal("4.00")
    return {
        "priced_seconds_per_sandbox": 8100,
        "full_profile_resource_bound_usd": str(full),
        "margin_usd": "0.10",
        "retained_usd": f"{retained:.2f}",
        "rounding": "upward_to_0.25USD",
        "actual_clock_cross_checks": records,
    }


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def observed_profile(full, prior):
    """Refine only a previously admitted full profile with identical clocks.

    Charge every complete creation-to-cleanup interval, with the original
    300-second allowance added at each end. No utilization or overlap credit.
    """
    assert prior["applied"] is True
    for key in (
        "priced_seconds_per_sandbox",
        "full_profile_resource_bound_usd",
        "margin_usd",
        "retained_usd",
        "rounding",
        "actual_clock_cross_checks",
    ):
        assert prior[key] == full[key], "The preceding full-profile proof changed"
    clocks = full["actual_clock_cross_checks"]
    assert set(clocks) == FOLDERS
    upper = sum(Decimal(row["resource_upper_bound_usd"]) for row in clocks.values())
    assert upper.is_finite() and 0 < upper <= Decimal(full["full_profile_resource_bound_usd"])
    keep = ((upper + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert 0 < keep < Decimal(full["retained_usd"])
    return {
        **full,
        "previous_full_profile_retained_usd": full["retained_usd"],
        "observed_full_lifetimes_resource_bound_usd": str(upper),
        "retained_usd": f"{keep:.2f}",
        "clock_basis": "Complete creation-to-cleanup interval plus300seconds at EACH end",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--closed-lifetimes-from", type=Path)
    parser.add_argument("--prior-helper-revision")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    args.proof = args.proof.resolve()
    assert bool(args.closed_lifetimes_from) == bool(args.prior_helper_revision)
    assert args.proof.is_relative_to(EXPERIMENT)
    assert not args.proof.exists()
    archive = args.private_root / f"archives/{args.number:03}"
    snapshot = archive / "snapshot-restored"
    readback = json.loads((archive / "failure-archive-readback.json").read_text())
    raw_manifest = (snapshot / "snapshot-files.json").read_bytes()
    assert readback["snapshot"]["source_manifest_sha256"] == digest(raw_manifest)
    assert readback["snapshot"]["all_snapshot_files_hash_size_mode_verified"]
    assert json.loads((archive / "root-evidence/readback.json").read_text())[
        "all_manifest_files_hash_size_mode_verified"
    ]
    rows = {row["path"]: row for row in json.loads(raw_manifest)["files"]}

    def original(name):
        raw = (snapshot / "files" / name).read_bytes()
        assert digest(raw) == rows[name]["sha256"] and len(raw) == rows[name]["bytes"]
        return json.loads(raw)

    pipeline = original("pipeline.json")
    assert pipeline["status"] == "infrastructure_failed" and pipeline["failed_stage"] == "grading"
    assert [row["name"] for row in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
    ]
    assert {
        name.removesuffix("/sandbox-claim.json")
        for name in rows
        if name.endswith("/sandbox-claim.json")
    } == FOLDERS
    repair = pipeline["quality_repair"]
    assert (
        repair["kind"] == "comparison_diagnosis"
        and repair["allowance_consumed"] is True
        and repair["target"] in {"public_question", "independent_solution"}
    )
    claim_path = args.private_root / f"launch/{args.number:03}-submission.json"
    claim_raw = claim_path.read_bytes()
    claim = json.loads(claim_raw)
    assert (
        digest(claim_raw) == readback["source_claim_sha256"]
        and pipeline["factory_revision"] == claim["factory_revision"]
    )
    terminal = max(
        (
            json.loads(path.read_text())
            for path in (args.private_root / "launch/typed-observations").glob(
                f"{args.number:03}-*.json"
            )
        ),
        key=lambda row: row["observed_at"],
    )
    assert (
        terminal["state"] == "FAILED"
        and terminal["terminal"]
        and terminal["claim_sha256"] == digest(claim_raw)
    )
    payload = args.private_root / f"launch/{args.number:03}-payload"
    packet = payload / "biotasks.tar"
    assert digest(packet.read_bytes()) == claim["inputs"]["files"]["biotasks.tar"]
    expected = json.loads((EXPERIMENT / "panel-rounds/103/runtime-identity.json").read_text())[
        "runtime_files"
    ]
    with tarfile.open(packet) as source:
        actual = {
            row.name: hashlib.file_digest(source.extractfile(row), "sha256").hexdigest()
            for row in source
            if row.isfile() and row.name in expected
        }
    assert actual == expected, "Unknown source family; retain the full reservation"
    fresh_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
    fresh = json.loads(fresh_raw)
    assert (
        fresh["complete"]
        and fresh["original_all_cleanup_passed"]
        and fresh["all_original_claim_ids_checked"]
        and fresh["fresh_original_ids_absent"]
        and not fresh["sandboxes"]
    )
    assert fresh["source_snapshot_manifest_sha256"] == digest(raw_manifest)
    sessions, identities, owners = {}, [], []
    for folder in sorted(FOLDERS):
        creation = original(folder + "/sandbox-claim.json")
        cleanup = original(folder + "/cleanup.json")
        assert creation["state"] == "created" and creation["resources"] == {
            "cpu": 4,
            "memory": 8,
            "disk": 10,
        }
        assert (
            cleanup["passed"] and not cleanup["remaining"] and not cleanup.get("creation_uncertain")
        )
        assert len(cleanup["sandboxes"]) == 1
        box = cleanup["sandboxes"][0]
        assert (
            box["id"] == creation["id"]
            and box["deleted"] is True
            and (box["cpu"], box["memory"], box["disk"]) == (4, 8, 10)
        )
        owners.append(creation["owner"])
        identities.append(creation["id"])
        sessions[folder] = original(folder + "/result.json")
    assert len(set(identities)) == 5 and sorted(fresh["owners"]) == sorted(owners)
    assert {row["id"] for row in fresh["original_sandbox_claims"]} == set(identities)
    priced = full_profile(sessions, pipeline)
    prior_record = {}
    old_hold = Decimal("5.00")
    if args.closed_lifetimes_from:
        assert re.fullmatch(r"[0-9a-f]{40}", args.prior_helper_revision)
        previous_raw = args.closed_lifetimes_from.read_bytes()
        previous = json.loads(previous_raw)
        repository = EXPERIMENT.parents[1]
        previous_helper = subprocess.check_output(
            [
                "git",
                "show",
                args.prior_helper_revision
                + ":"
                + Path(__file__).resolve().relative_to(repository).as_posix(),
            ],
            cwd=repository,
        )
        assert digest(previous_helper) == previous["helper_sha256"]
        assert previous["campaign"] == args.number
        assert previous["source_snapshot_manifest_sha256"] == digest(raw_manifest)
        assert previous["source_claim_sha256"] == digest(claim_raw)
        assert previous["fresh_cleanup_sha256"] == digest(fresh_raw)
        assert previous["original_clock_hashes"] == {
            folder + "/result.json": rows[folder + "/result.json"]["sha256"]
            for folder in sorted(FOLDERS)
        }
        priced = observed_profile(priced, previous)
        old_hold = Decimal(previous["retained_usd"])
        prior_record = {
            "preceding_full_profile_proof_sha256": digest(previous_raw),
            "preceding_helper_revision": args.prior_helper_revision,
            "preceding_helper_sha256": digest(previous_helper),
        }
    ledger_path = EXPERIMENT / "aggregate-budget.json"
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"])
    row = next(
        row
        for row in ledger["reservations"]
        if row["scope"].startswith(f"autonomous-panel-{args.number:03}:")
    )
    assert Decimal(row["ceiling_usd"]) == old_hold
    if args.closed_lifetimes_from:
        assert row["state"] == "terminal_five_sdk_full_profile_reconciled"
        assert row["reconciliation"].endswith(
            args.closed_lifetimes_from.resolve().relative_to(EXPERIMENT).as_posix()
        )
    row.update(
        ceiling_usd=priced["retained_usd"],
        state=(
            "terminal_five_sdk_observed_clock_refined"
            if args.closed_lifetimes_from
            else "terminal_five_sdk_full_profile_reconciled"
        ),
        reconciliation=(
            "Complete original creation-to-cleanup clocks plus300seconds at EACH end for EACH of5verified SDK sessions,0.10margin/quarter-dollar upward rounding; no serialization/idle/invoice/credit assumptions. See "
            if args.closed_lifetimes_from
            else "Full125minute lifetime plus300seconds at EACH end for EACH of5verified SDK sessions,0.10margin/quarter-dollar upward rounding; no serialization/idle/invoice/credit assumptions. See "
        )
        + args.proof.relative_to(EXPERIMENT).as_posix(),
    )
    released = old_hold - Decimal(priced["retained_usd"])
    ledger.update(
        reserved_upper_bound_usd=f"{held - released:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held + released:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "campaign": args.number,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "source_snapshot_manifest_sha256": digest(raw_manifest),
        "source_claim_sha256": digest(claim_raw),
        "fresh_cleanup_sha256": digest(fresh_raw),
        "terminal": terminal,
        **prior_record,
        "original_clock_hashes": {
            folder + "/result.json": rows[folder + "/result.json"]["sha256"]
            for folder in sorted(FOLDERS)
        },
        **priced,
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "released_usd": str(released),
        "aggregate_held_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "actual_provider_invoice_usd": None,
        "credits_assumed": False,
        "new_campaign_full_reservation_unchanged": "5.00",
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if args.apply:
        assert ledger_path.read_bytes() == before
        ledger_path.write_bytes(after)
    print(
        json.dumps(
            {
                key: value
                for key, value in proof.items()
                if key not in ("actual_clock_cross_checks", "original_clock_hashes")
            }
        )
    )


if __name__ == "__main__":
    main()
