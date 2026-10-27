"""Refine used setup/replay holds after complete original-bound verification.

Operator accounting only. The full new-campaign reservation remains $5. Admit
only the recorded 103–105 resource family, no native trials, no uncertain
creations and no manual deletion assumptions. Price every complete lifetime
plus the original 300-second cleanup allowance at EACH end.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/070"))
from closed_session_bound import closed_session_bound  # noqa: E402

CREATOR = "cfeefdda2dc0f2ba4a62618e9202b6ef3af038a48ff78a35337e1567fcfe25f3"
CONTROLLER = "7ff0e8dbcc69ebaf927c431740eb63ad2965a507514d349ca3767aff6187c685"
SESSIONS = {
    "6fff50b96c0df7488057a0e14f9ab277549843418ad9a6144930884c4af18475",
    "be1e5009087203457ee9ccaae19774cf0624a9a76a300cc431a4637f210218da",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def profile(pipeline):
    """No scientific outcome is relabelled by this accounting classification."""
    assert pipeline["operator_interventions"] == 0 and not pipeline.get("quality_repair")
    rows = pipeline["stages"]
    shape = [(row["name"], row["status"]) for row in rows]
    if shape == [("preparation", "completed"), ("setup", "rejected")]:
        assert pipeline["status"] == "rejected" and not pipeline.get("failed_stage")
        folders, terminal = ["setup-raw"], "SUCCEEDED"
    else:
        assert shape == [
            ("preparation", "completed"),
            ("setup", "completed"),
            ("replay", "incomplete"),
        ]
        assert (
            pipeline["status"] == "infrastructure_failed" and pipeline["failed_stage"] == "replay"
        )
        folders, terminal = ["setup-raw", "replay"], "FAILED"
    assert pipeline["daytona_reserved_usd"] == len(folders)
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert pipeline["started"] <= rows[0]["started"]
    assert rows[-1]["finished"] <= pipeline["finished"]
    assert all(row["started"] <= row["finished"] for row in rows)
    assert all(a["finished"] <= b["started"] for a, b in zip(rows, rows[1:], strict=False))
    return folders, terminal


def price(pipeline, sessions):
    folders, _ = profile(pipeline)
    assert set(sessions) == set(folders)
    records = {}
    for folder in folders:
        stage = next(
            row for row in pipeline["stages"] if row["name"] == folder.removesuffix("-raw")
        )
        session = sessions[folder]
        assert stage["started"] <= session["started"] < session["finished"] <= stage["finished"]
        records[folder] = closed_session_bound(session, pipeline, [], 300)
    upper = sum(Decimal(row["resource_upper_bound_usd"]) for row in records.values())
    retained = ((upper + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert 0 < upper <= retained < len(folders)
    return records, upper, retained


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("number", type=int)
    p.add_argument("--runtime-round", type=int, choices=(103, 104, 105), required=True)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--prior-unused-proof", type=Path, required=True)
    p.add_argument("--proof", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    assert not args.proof.exists()
    assert args.proof.resolve().is_relative_to(EXPERIMENT)
    spec = importlib.util.spec_from_file_location(
        "recorded_sdk_archive_reader",
        EXPERIMENT / "panel-rounds/079/reconcile_setup_replay_prefix.py",
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    archive = args.private_root / f"archives/{args.number:03}"
    content, manifest, manifest_hash, _ = reader.archive_inventory(archive)
    checked = {}

    def original(name):
        path = content / name
        assert not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == manifest[name]["bytes"] and digest(raw) == manifest[name]["sha256"]
        checked[name] = digest(raw)
        return json.loads(raw)

    pipeline = original("pipeline.json")
    folders, terminal = profile(pipeline)
    assert {
        name.removesuffix("/sandbox-claim.json")
        for name in manifest
        if name.endswith("/sandbox-claim.json")
    } == set(folders)
    assert not any(name.startswith("native/") for name in manifest)
    previous_raw = args.prior_unused_proof.read_bytes()
    previous = json.loads(previous_raw)
    assert previous["applied"] is True
    assert previous["reconciliation_helper_sha256"] == digest(
        (EXPERIMENT / "panel-rounds/037/reconcile_unused_stages.py").read_bytes()
    )
    prior = next(row for row in previous["records"] if row["campaign"] == args.number)
    assert prior["source_archive_manifest_sha256"] == manifest_hash
    assert prior["dispatched_stages"] == [folder.removesuffix("-raw") for folder in folders]
    assert Decimal(prior["retained_full_dispatched_stage_hold_usd"]) == len(folders)
    assert prior["terminal"]["state"] == terminal and prior["terminal"]["terminal"] is True
    launch = args.private_root / "launch"
    claim_raw = (launch / f"{args.number:03}-submission.json").read_bytes()
    claim = json.loads(claim_raw)
    assert prior["terminal"]["claim_sha256"] == digest(claim_raw)
    assert pipeline["factory_revision"] == claim["factory_revision"]
    payload = launch / f"{args.number:03}-payload"
    config_raw = (payload / "campaign-config.json").read_bytes()
    assert digest(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
    config = json.loads(config_raw)
    assert (
        config["campaign_seconds"],
        config["cleanup_seconds"],
        config["daytona_budget_usd"],
    ) == (7200, 300, "5.00")
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }
    round_root = EXPERIMENT / f"panel-rounds/{args.runtime_round}"
    admission_raw = (round_root / "source-admission.json").read_bytes()
    admission = json.loads(admission_raw)
    assert (
        digest((round_root / "runtime_admission.py").read_bytes())
        == admission["admission_helper_sha256"]
    )
    identity_raw = (round_root / "runtime-identity.json").read_bytes()
    runtime = json.loads(identity_raw)["runtime_files"]
    assert len(runtime) == 232
    assert runtime[PREFIX + "run_autonomous.py"] == CONTROLLER
    assert runtime[PREFIX + "run_reference_setup.py"] == CREATOR
    assert runtime[PREFIX + "reference_setup.py"] in SESSIONS
    packet = payload / "biotasks.tar"
    with packet.open("rb") as stream:
        assert (
            hashlib.file_digest(stream, "sha256").hexdigest()
            == claim["inputs"]["files"]["biotasks.tar"]
        )
    with tarfile.open(packet) as stream:
        reader.check_common_payload(stream, config, runtime)
    cleanup_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
    cleanup = json.loads(cleanup_raw)
    assert cleanup["source_archive_manifest_sha256"] == manifest_hash
    assert cleanup["source_configuration_sha256"] == digest(config_raw)
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["all_original_sdk_claim_ids_checked"] and cleanup["fresh_original_ids_absent"]
    assert not cleanup["sandboxes"] and not cleanup["native_unrecorded_id_owners"]
    claims, sessions = [], {}
    for folder in folders:
        created, deleted = (
            original(folder + "/sandbox-claim.json"),
            original(folder + "/cleanup.json"),
        )
        assert created["state"] == "created" and created["resources"] == {
            "cpu": 4,
            "memory": 8,
            "disk": 10,
        }
        assert (
            deleted["passed"] and not deleted["remaining"] and not deleted.get("creation_uncertain")
        )
        assert deleted["sandboxes"] == [
            {"id": created["id"], "cpu": 4, "memory": 8, "disk": 10, "deleted": True}
        ]
        claims.append(created)
        sessions[folder] = original(folder + "/result.json")
    assert (
        len({row["id"] for row in claims}) == len({row["owner"] for row in claims}) == len(folders)
    )
    assert sorted(row["owner"] for row in claims) == sorted(cleanup["owners"])
    assert sorted(claims, key=lambda row: row["id"]) == sorted(
        cleanup["original_sdk_claims"], key=lambda row: row["id"]
    )
    clocks, upper, retained = price(pipeline, sessions)
    ledger_path = EXPERIMENT / "aggregate-budget.json"
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    assert sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"]) == Decimal(
        ledger["reserved_upper_bound_usd"]
    )
    row = next(
        row
        for row in ledger["reservations"]
        if row["scope"].startswith(f"autonomous-panel-{args.number:03}:")
    )
    assert row["state"] == "unused_stage_allowances_released_used_holds_unchanged"
    assert Decimal(row["ceiling_usd"]) == len(folders)
    row.update(
        ceiling_usd=f"{retained:.2f}",
        state="terminal_original_closed_sdk_prefix_refined",
        reconciliation="Every original creation-to-cleanup lifetime plus300seconds at EACH end;0.10margin/quarter-dollar upward rounding; no scientific outcome, invoice, credits or new5USDreservation changed. See "
        + args.proof.resolve().relative_to(EXPERIMENT).as_posix(),
    )
    held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
    ledger.update(
        reserved_upper_bound_usd=f"{held:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "campaign": args.number,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "source_archive_manifest_sha256": manifest_hash,
        "source_claim_sha256": digest(claim_raw),
        "source_runtime_identity_sha256": digest(identity_raw),
        "source_admission_sha256": digest(admission_raw),
        "fresh_cleanup_sha256": digest(cleanup_raw),
        "prior_unused_stage_proof_sha256": digest(previous_raw),
        "checked_originals": checked,
        "terminal": prior["terminal"],
        "closed_sessions": clocks,
        "resource_upper_bound_usd": str(upper),
        "margin_usd": "0.10",
        "rounding": "upward_to_0.25USD",
        "retained_usd": f"{retained:.2f}",
        "released_usd": f"{Decimal(len(folders)) - retained:.2f}",
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "aggregate_held_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "new_campaign_full_reservation_unchanged": "5.00",
        "actual_provider_invoice_usd": None,
        "credits_assumed": False,
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
                if key not in {"closed_sessions", "checked_originals"}
            }
        )
    )


if __name__ == "__main__":
    main()
