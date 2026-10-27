"""Refine completed synthetic controls; never lower a new campaign reservation."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/070"))
from closed_session_bound import RATE, closed_session_bound, number  # noqa: E402

CREATOR = "experiments/19-repo2rlenv-notebook-pilot/factory-checks/daytona-session-transport/run_live_check.py"
CREATOR_SHA = "928fcce5a865a99e796e0752434f8f397d6094821781e34d9da5a4325e57b457"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_control(config, result, claim, cleanup, fresh):
    assert config["resources"] == {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False}
    assert (
        config["seconds"],
        config["cleanup_seconds"],
        config["reservation_usd"],
        config["model_calls"],
    ) == (300, 180, "1.00", 0)
    assert config["source_sha256"][CREATOR] == CREATOR_SHA
    assert result["status"] == "compatibility_observed" and result["cleanup_verified"] is True
    assert result["new_model_calls"] == 0 and result["scientific_computation"] is False
    assert len(result["cases"]) == 3 and all(row["passed"] is True for row in result["cases"])
    assert 0 < number(result["finished"]) - number(result["started"]) <= 480
    assert claim["state"] == "created" and claim["owner"] == config["owner"]
    assert claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    assert cleanup["passed"] is True and cleanup["remaining"] == []
    assert not cleanup.get("creation_uncertain")
    assert len(cleanup["sandboxes"]) == 1
    box = cleanup["sandboxes"][0]
    assert box["id"] == claim["id"] and box["deleted"] is True
    assert (box["cpu"], box["memory"], box["disk"]) == (4, 8, 10)
    assert all(
        fresh[key] is True
        for key in (
            "complete",
            "fresh_original_id_absent",
            "fresh_owner_list_empty",
            "original_cleanup_verified",
        )
    )
    assert fresh["owner"] == config["owner"] and fresh["original_id"] == claim["id"]
    observed = datetime.fromisoformat(fresh["observed_at"])
    assert observed.tzinfo is not None and number(observed.timestamp()) >= number(
        result["finished"]
    )
    actual = closed_session_bound(result, result, [], 300)
    # Charge the ENTIRE approved480seconds, plus300seconds at each end,
    # even when the actual completed control was much shorter.
    full = Decimal(1080) * RATE / 3600
    assert Decimal(actual["resource_upper_bound_usd"]) <= full
    retained = ((full + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert retained == Decimal("0.25")
    return {
        "full_approved_lifetime_plus_margins_seconds": 1080,
        "resource_upper_bound_usd": str(full),
        "actual_closed_clock_cross_check": actual,
        "retained_usd": f"{retained:.2f}",
        "margin_usd": "0.10",
        "rounding": "upward_to_0.25USD",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    args.proof = args.proof.resolve()
    assert args.proof.is_relative_to(EXPERIMENT)
    assert not args.proof.exists()
    before = args.ledger.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"])
    records, used = [], set()
    repo = EXPERIMENT.parents[1]
    for member in json.loads(args.plan.read_text())["members"]:
        public = (EXPERIMENT / member["public_directory"]).resolve()
        private = (args.private_root / member["private_directory"]).resolve()
        assert public.is_relative_to(EXPERIMENT) and private.is_relative_to(args.private_root)
        blobs = {
            name: (private / name).read_bytes()
            for name in (
                "configuration.json",
                "result.json",
                "sandbox-claim.json",
                "cleanup.json",
                "fresh-provider-cleanup.json",
            )
        }
        config, result, claim, cleanup, fresh = [json.loads(blobs[name]) for name in blobs]
        public_config = (public / "live-check-configuration.json").read_bytes()
        public_fresh = (public / "live-fresh-provider-cleanup.json").read_bytes()
        summary = json.loads((public / "integration-summary.json").read_text())
        assert (
            json.loads(public_config) == config
            and public_fresh == blobs["fresh-provider-cleanup.json"]
        )
        assert summary["source_configuration_sha256"] == digest(public_config)
        assert summary["source_result_sha256"] == digest(blobs["result.json"])
        assert summary["fresh_cleanup_sha256"] == digest(public_fresh)
        assert fresh["original_cleanup_sha256"] == digest(blobs["cleanup.json"])
        assert fresh["captured_configuration_sha256"] == digest(blobs["configuration.json"])
        for name, sha in config["source_sha256"].items():
            path = (repo / name).resolve()
            assert path.is_relative_to(repo) and digest(path.read_bytes()) == sha
        priced = bounded_control(config, result, claim, cleanup, fresh)
        reference = (public / "live-check-configuration.json").relative_to(EXPERIMENT).as_posix()
        matches = [row for row in ledger["reservations"] if row.get("configuration") == reference]
        assert len(matches) == 1 and reference not in used
        used.add(reference)
        row = matches[0]
        assert row["ceiling_usd"] == "1.00" and row["state"] in {
            "terminal_compatibility_original_cleanup_verified",
            "terminal_compatibility_cleanup_verified",
        }
        row.update(
            ceiling_usd=priced["retained_usd"],
            state="terminal_synthetic_control_full_profile_reconciled",
            reconciliation="Full approved480seconds plus300seconds at each end, original/independent cleanup verified;0.10USDmargin and upward quarter-dollar rounding. No invoice or credits. See "
            + args.proof.relative_to(EXPERIMENT).as_posix(),
        )
        records.append(
            {
                "configuration": reference,
                "source_originals": {name: digest(raw) for name, raw in blobs.items()},
                **priced,
            }
        )
    released = sum(Decimal("1.00") - Decimal(row["retained_usd"]) for row in records)
    ledger.update(
        reserved_upper_bound_usd=f"{held - released:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held + released:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "plan_sha256": digest(args.plan.read_bytes()),
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "records": records,
        "released_usd": str(released),
        "aggregate_held_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "actual_provider_invoice_usd": None,
        "credits_assumed": False,
        "new_campaign_full_reservation_unchanged": "5.00",
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if args.apply:
        assert args.ledger.read_bytes() == before
        args.ledger.write_bytes(after)
    print(json.dumps({key: value for key, value in proof.items() if key != "records"}))


if __name__ == "__main__":
    main()
