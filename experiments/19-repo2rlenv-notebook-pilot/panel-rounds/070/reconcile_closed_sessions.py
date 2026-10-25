"""Refine an already admitted SDK-only profile using complete closed lifetimes."""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from closed_session_bound import (
    RATE,
    admitted_implementation,
    admitted_profile,
    closed_session_bound,
    terminal_state,
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--prior-proof", type=Path, required=True)
    parser.add_argument(
        "--prior-helper-revision",
        help="Exact Git commit retaining the preceding auditor, if its current file changed",
    )
    parser.add_argument("--usage", type=Path)
    parser.add_argument(
        "--without-analytics",
        action="store_true",
        help="Use complete source-verified controller lifetimes only; no provider price claim",
    )
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert bool(args.usage) != args.without_analytics
    assert not args.proof.exists()
    previous_raw = args.prior_proof.read_bytes()
    previous = json.loads(previous_raw)
    folders, prior_retained, prior_implementation = admitted_profile(previous)
    prior_helper = Path(__file__).resolve().parents[1] / prior_implementation
    if args.prior_helper_revision:
        assert re.fullmatch(r"[0-9a-f]{40}", args.prior_helper_revision)
        repository = Path(__file__).resolve().parents[4]
        prior_raw = subprocess.check_output(
            [
                "git",
                "show",
                args.prior_helper_revision + ":" + prior_helper.relative_to(repository).as_posix(),
            ],
            cwd=repository,
        )
    else:
        prior_raw = prior_helper.read_bytes()
    assert digest(prior_raw) == previous["helper_sha256"]
    number = previous["campaign"]
    archive = args.private_root / f"archives/{number:03}"
    manifest_raw = (archive / "sealed-manifest.json").read_bytes()
    manifest_hash = digest(manifest_raw)
    assert previous["source_manifest_sha256"] == manifest_hash
    manifest = {item["path"]: item for item in json.loads(manifest_raw)["files"]}
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert (
        readback["all_files_download_verified"]
        and readback["source_manifest_sha256"] == manifest_hash
    )
    assert json.loads((archive / "root-evidence/readback.json").read_text())[
        "all_manifest_files_hash_size_mode_verified"
    ]
    checked = {}

    def original(name):
        raw = (archive / "files" / name).read_bytes()
        assert digest(raw) == manifest[name]["sha256"] and len(raw) == manifest[name]["bytes"]
        checked[name] = digest(raw)
        return json.loads(raw)

    for name, expected in previous["checked_originals"].items():
        original(name)
        assert checked[name] == expected
    pipeline = original("pipeline.json")
    expected_terminal = terminal_state(pipeline)
    if len(folders) == 4:
        assert not pipeline.get("quality_repair")
    expected_sources = admitted_implementation(previous["frozen_implementation_sha256"])
    launch = args.private_root / "launch"
    claim_raw = (launch / f"{number:03}-submission.json").read_bytes()
    claim = json.loads(claim_raw)
    assert previous["terminal"]["state"] == expected_terminal and previous["terminal"]["terminal"]
    assert previous["terminal"]["claim_sha256"] == digest(claim_raw)
    payload = launch / f"{number:03}-payload"
    packet = payload / "biotasks.tar"
    assert digest(packet.read_bytes()) == claim["inputs"]["files"]["biotasks.tar"]
    with tarfile.open(packet) as source:
        for name, expected in expected_sources.items():
            raw = source.extractfile("experiments/19-repo2rlenv-notebook-pilot/" + name).read()
            assert digest(raw) == expected
    config_raw = (payload / "campaign-config.json").read_bytes()
    assert digest(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
    config = json.loads(config_raw)
    assert config["campaign_seconds"] == 7200 and config["cleanup_seconds"] == 300
    assert config["daytona_budget_usd"] == "5.00"
    clean_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
    clean = json.loads(clean_raw)
    assert clean["source_archive_manifest_sha256"] == manifest_hash
    assert clean["source_configuration_sha256"] == digest(config_raw)
    assert clean["complete"] and clean["original_all_cleanup_passed"]
    assert clean["fresh_original_ids_absent"] and not clean["sandboxes"]
    usage_raw = args.usage.read_bytes() if args.usage else None
    usage = json.loads(usage_raw) if usage_raw is not None else None
    if usage is not None:
        assert usage["campaign"] == number
        assert usage["source_archive_manifest_sha256"] == manifest_hash
    assert {name for name in manifest if name.endswith("/sandbox-claim.json")} == {
        name + "/sandbox-claim.json" for name in folders
    }
    assert not any(name.startswith("native/") for name in manifest)
    if usage is not None:
        assert len(usage["records"]) == len(folders)
        assert {r["stage"] for r in usage["records"]} == folders
    owners, ids, records = [], [], []
    for folder in sorted(folders):
        created = original(folder + "/sandbox-claim.json")
        cleanup = original(folder + "/cleanup.json")
        assert created["state"] == "created"
        assert created["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
        periods = []
        if usage is not None:
            observation = next(r for r in usage["records"] if r["stage"] == folder)
            assert observation["http_status"] == 200
            assert observation["original_claim_sha256"] == checked[folder + "/sandbox-claim.json"]
            assert observation["sandbox_id"] == created["id"]
            periods = observation["records"]
            assert periods
        assert (
            cleanup["passed"]
            and not cleanup.get("creation_uncertain")
            and not cleanup.get("remaining")
        )
        assert cleanup["sandboxes"] == [
            {"id": created["id"], "cpu": 4, "memory": 8, "disk": 10, "deleted": True}
        ]
        owners.append(created["owner"])
        ids.append(created["id"])
        result = closed_session_bound(
            original(folder + "/result.json"),
            pipeline,
            periods,
            config["cleanup_seconds"],
        )
        records.append({"stage": folder, **result})
    assert len(set(ids)) == len(set(owners)) == len(folders) and set(owners) == set(clean["owners"])
    upper = sum(Decimal(r["resource_upper_bound_usd"]) for r in records)
    assert 0 < upper < 1
    before = args.ledger.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"])
    row = next(
        r for r in ledger["reservations"] if r["scope"].startswith(f"autonomous-panel-{number:03}:")
    )
    assert (
        row["ceiling_usd"] == f"{prior_retained:.2f}"
        and row["state"] == "terminal_sdk_only_all_lifetimes_bound_reconciled"
    )
    assert args.prior_proof.relative_to(args.ledger.parent).as_posix() in row["reconciliation"]
    row.update(
        ceiling_usd="1.00",
        state="terminal_full_closed_sdk_lifetimes_bound_reconciled",
        reconciliation="Exact known creator, all recorded closed controller lifetimes priced at full resources plus300s at each end and fresh cleanup. Provider analytics is recorded separately when available and never shortens a lifetime. Retain1USD; no credits or final invoice assumption. See "
        + args.proof.relative_to(args.ledger.parent).as_posix(),
    )
    released = prior_retained - Decimal(1)
    ledger.update(
        reserved_upper_bound_usd=f"{held - released:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held + released:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": number,
        "applied": args.apply,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "profile_helper_sha256": digest(
            Path(__file__).with_name("closed_session_bound.py").read_bytes()
        ),
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "prior_proof_sha256": digest(previous_raw),
        "prior_helper_revision": args.prior_helper_revision,
        "prior_helper_sha256": digest(prior_raw),
        "source_manifest_sha256": manifest_hash,
        "checked_originals": checked,
        "known_implementation_sha256": expected_sources,
        "fresh_cleanup_sha256": digest(clean_raw),
        "fresh_cleanup_observed_at": clean["observed_at"],
        "usage_receipt_sha256": digest(usage_raw) if usage_raw is not None else None,
        "provider_usage_crosscheck": "available"
        if usage is not None
        else "unavailable_not_used_in_bound",
        "records": records,
        "hourly_full_resource_rate_usd": str(RATE),
        "resource_upper_bound_usd": str(upper),
        "retained_usd": "1.00",
        "released_usd": f"{released:.2f}",
        "aggregate_reserved_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "actual_provider_invoice_usd": None,
        "free_credits_assumed": False,
        "new_models_or_provider_resources": 0,
        "original_execution_limits_or_scientific_outcomes_changed": False,
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if args.apply:
        assert args.ledger.read_bytes() == before
        args.ledger.write_bytes(after)
    print(json.dumps({k: v for k, v in proof.items() if k not in {"records", "checked_originals"}}))


if __name__ == "__main__":
    main()
