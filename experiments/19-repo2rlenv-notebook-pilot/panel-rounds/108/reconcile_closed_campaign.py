"""Refine closed SDK holds while retaining the original full native-stage hold.

Accounting only: exact frozen72/105/108 sources, complete original archives, terminal
observations and fresh ID/owner cleanup are required. No scientific verdict,
new-campaign reservation, time allowance or invoice claim changes.
"""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/070"))
from closed_session_bound import closed_session_bound  # noqa: E402

BASE = {"setup-raw", "replay", "materialization-raw", "grading"}


def rejected_profile(pipeline):
    """Price only known completed SDK prefixes ending in an ordinary rejection."""
    assert pipeline["autonomous"] is True and pipeline["operator_interventions"] == 0
    stages = pipeline["stages"]
    names = [row["name"] for row in stages]
    prefixes = {
        ("preparation", "setup"): {"setup-raw"},
        ("preparation", "setup", "replay", "specification"): {"setup-raw", "replay"},
        ("preparation", "setup", "replay", "specification", "construction", "grading"): BASE,
    }
    assert tuple(names) in prefixes
    assert [row["status"] for row in stages] == ["completed"] * (len(stages) - 1) + ["rejected"]
    assert not pipeline.get("failed_stage")
    assert pipeline["rejection"]["stage"] == names[-1]
    folders = prefixes[tuple(names)]
    assert pipeline["daytona_reserved_usd"] == len(folders)
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert pipeline["started"] <= stages[0]["started"]
    assert stages[-1]["finished"] <= pipeline["finished"]
    assert all(row["started"] <= row["finished"] for row in stages)
    assert all(a["finished"] <= b["started"] for a, b in zip(stages, stages[1:], strict=False))
    repair = pipeline.get("quality_repair")
    if names[-1] == "setup":
        assert repair is None
    if repair is not None:
        assert repair["kind"] == "specification_review"
        assert repair["target"] == "task_specification" and repair["allowance_consumed"] is True
    return set(folders), Decimal("0.00")


def profile(pipeline):
    if pipeline.get("status") == "rejected":
        return rejected_profile(pipeline)
    assert pipeline["autonomous"] is True and pipeline["operator_interventions"] == 0
    assert pipeline["status"] == "infrastructure_failed"
    stages = pipeline["stages"]
    names = [row["name"] for row in stages]
    base = ["preparation", "setup", "replay", "specification", "construction", "grading"]
    native = names == base + ["native"]
    assert native or names == base
    assert [row["status"] for row in stages] == ["completed"] * (len(stages) - 1) + ["incomplete"]
    assert pipeline["failed_stage"] == names[-1]
    assert pipeline["daytona_reserved_usd"] == (5 if native else 4)
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert pipeline["started"] <= stages[0]["started"]
    assert stages[-1]["finished"] <= pipeline["finished"]
    assert all(row["started"] <= row["finished"] for row in stages)
    assert all(a["finished"] <= b["started"] for a, b in zip(stages, stages[1:], strict=False))
    repair = pipeline.get("quality_repair")
    assert repair and repair["allowance_consumed"] is True
    if native:
        assert repair["kind"] == "specification_review"
        return BASE, Decimal("1.00")
    assert repair["kind"] in {"comparison_diagnosis", "public_question_diagnosis"}
    assert repair["target"] in {"public_question", "independent_solution"}
    assert repair["kind"] != "public_question_diagnosis" or repair["target"] == "public_question"
    return BASE | {"grading-comparison-repair"}, Decimal("0.00")


def price(pipeline, sessions):
    folders, native_hold = profile(pipeline)
    assert set(sessions) == folders
    stage_names = {
        "setup-raw": "setup",
        "materialization-raw": "construction",
        "grading-comparison-repair": "grading",
    }
    stages = {row["name"]: row for row in pipeline["stages"]}
    clocks = {}
    for folder, session in sessions.items():
        stage = stages[stage_names.get(folder, folder)]
        assert stage["started"] <= session["started"] < session["finished"] <= stage["finished"]
        clocks[folder] = closed_session_bound(session, pipeline, [], 300)
    upper = sum(Decimal(row["resource_upper_bound_usd"]) for row in clocks.values())
    retained = ((upper + native_hold + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert 0 < upper and upper + native_hold < retained <= Decimal("5.00")
    return clocks, upper, native_hold, retained


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def admit_resource_family(runtime, version, native_hold):
    if version in (105, 108):
        count, expected = (
            232,
            (
                "7ff0e8dbcc69ebaf927c431740eb63ad2965a507514d349ca3767aff6187c685",
                "cfeefdda2dc0f2ba4a62618e9202b6ef3af038a48ff78a35337e1567fcfe25f3",
                "be1e5009087203457ee9ccaae19774cf0624a9a76a300cc431a4637f210218da",
            ),
        )
    else:
        assert version == 72 and native_hold == 0
        count, expected = (
            217,
            (
                "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188",
                "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8",
                "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7",
            ),
        )
    assert len(runtime) == count
    assert (
        tuple(
            runtime[PREFIX + name]
            for name in ("run_autonomous.py", "run_reference_setup.py", "reference_setup.py")
        )
        == expected
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--runtime-round", type=int, choices=(72, 105, 108), default=105)
    parser.add_argument("--previous-unused-proof", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.proof.exists() and args.proof.resolve().is_relative_to(EXPERIMENT)
    spec = importlib.util.spec_from_file_location(
        "closed_archive_inventory", EXPERIMENT / "panel-rounds/079/reconcile_setup_replay_prefix.py"
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    archive = args.private_root / f"archives/{args.number:03}"
    content, rows, manifest_hash, recovery = reader.archive_inventory(
        archive, snapshot=args.snapshot
    )
    checked = {}

    def original(name):
        path = content / name
        assert not path.is_symlink() and path.stat().st_mode & 0o777 == rows[name]["mode"]
        raw = path.read_bytes()
        assert len(raw) == rows[name]["bytes"] and digest(raw) == rows[name]["sha256"]
        checked[name] = digest(raw)
        return json.loads(raw)

    pipeline = original("pipeline.json")
    folders, native_hold = profile(pipeline)
    assert {
        name.removesuffix("/sandbox-claim.json")
        for name in rows
        if name.endswith("/sandbox-claim.json")
    } == folders
    assert any(name.startswith("native/") for name in rows) is bool(native_hold)
    launch = args.private_root / "launch"
    claim_raw = (launch / f"{args.number:03}-submission.json").read_bytes()
    claim = json.loads(claim_raw)
    if args.snapshot:
        assert recovery["source_claim_sha256"] == digest(claim_raw)
        assert recovery["original_bootstrap_sha256"] == claim["inputs"]["files"]["bootstrap.py"]
    assert pipeline["factory_revision"] == claim["factory_revision"]
    terminal = max(
        (
            json.loads(path.read_text())
            for path in (launch / "typed-observations").glob(f"{args.number:03}-*.json")
        ),
        key=lambda row: row["observed_at"],
    )
    expected_terminal = "SUCCEEDED" if pipeline["status"] == "rejected" else "FAILED"
    assert terminal["state"] == expected_terminal and terminal["terminal"]
    assert terminal["claim_sha256"] == digest(claim_raw)
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
    runtime_raw = (
        EXPERIMENT / f"panel-rounds/{args.runtime_round:03}/runtime-identity.json"
    ).read_bytes()
    runtime = json.loads(runtime_raw)["runtime_files"]
    admit_resource_family(runtime, args.runtime_round, native_hold)
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
    assert (
        cleanup["complete"]
        and cleanup["original_all_cleanup_passed"]
        and cleanup["fresh_original_ids_absent"]
    )
    assert not cleanup["sandboxes"] and cleanup["source_configuration_sha256"] == digest(config_raw)
    assert (
        cleanup.get("source_archive_manifest_sha256")
        or cleanup.get("source_snapshot_manifest_sha256")
    ) == manifest_hash
    claims, sessions = [], {}
    for folder in sorted(folders):
        created = original(folder + "/sandbox-claim.json")
        deleted = original(folder + "/cleanup.json")
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
        stage_config = original(folder + "/configuration.json")
        assert stage_config["campaign"] == created["owner"] and created["owner"].startswith(
            config["campaign"] + "-"
        )
        claims.append(created)
        sessions[folder] = original(folder + "/result.json")
    assert (
        len({row["id"] for row in claims}) == len({row["owner"] for row in claims}) == len(folders)
    )
    direct_key, claim_key = (
        ("all_original_sdk_claim_ids_checked", "original_sdk_claims")
        if "all_original_sdk_claim_ids_checked" in cleanup
        else ("all_original_claim_ids_checked", "original_sandbox_claims")
    )
    assert cleanup[direct_key] and sorted(cleanup[claim_key], key=lambda row: row["id"]) == sorted(
        claims, key=lambda row: row["id"]
    )
    if native_hold:
        assert cleanup["native_undispatched_preflight_claims"]
        proof = cleanup["native_undispatched_preflight_claims"][0]
        assert (
            proof["dispatch_disproven_by_original_trace_and_exact_source"]
            and not proof["original_outcome_receipt_present"]
        )
        assert len(cleanup["owners"]) == len(folders) + 2
    else:
        assert sorted(cleanup["owners"]) == sorted(row["owner"] for row in claims)
    clocks, upper, native_hold, retained = price(pipeline, sessions)
    ledger_path = EXPERIMENT / "aggregate-budget.json"
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
    assert (
        held
        == Decimal(ledger["reserved_upper_bound_usd"])
        <= Decimal(ledger["ceiling_before_credits"])
        == Decimal("200.00")
    )
    row = next(
        row
        for row in ledger["reservations"]
        if row["scope"].startswith(f"autonomous-panel-{args.number:03}:")
    )
    prior_hold = Decimal(row["ceiling_usd"])
    previous_unused_hash = None
    if args.previous_unused_proof is None:
        assert prior_hold == 5
    else:
        assert not native_hold and pipeline["status"] == "rejected"
        previous_path = args.previous_unused_proof.resolve()
        relative = previous_path.relative_to(EXPERIMENT.resolve())
        previous_raw = previous_path.read_bytes()
        # This must be the committed output of the unchanged unused-stage audit,
        # not a new caller-written assertion about a lower starting hold.
        committed = subprocess.check_output(
            ["git", "show", "HEAD:" + PREFIX + relative.as_posix()], cwd=EXPERIMENT.parents[1]
        )
        assert committed == previous_raw
        previous = json.loads(previous_raw)
        assert previous["applied"] is True
        assert previous["reconciliation_helper_sha256"] == digest(
            (EXPERIMENT / "panel-rounds/037/reconcile_unused_stages.py").read_bytes()
        )
        candidates = [r for r in previous["records"] if r["campaign"] == args.number]
        assert len(candidates) == 1
        earlier = candidates[0]
        assert earlier["source_archive_manifest_sha256"] == manifest_hash
        assert earlier["terminal"]["claim_sha256"] == digest(claim_raw)
        assert earlier["prior_hold_usd"] == "5.00"
        assert prior_hold == Decimal(earlier["retained_full_dispatched_stage_hold_usd"])
        mapping = {"setup-raw": "setup", "materialization-raw": "construction"}
        assert set(earlier["dispatched_stages"]) == {mapping.get(n, n) for n in folders}
        assert row["state"] == "unused_stage_allowances_released_used_holds_unchanged"
        assert str(relative) in row["reconciliation"]
        previous_unused_hash = digest(previous_raw)
    assert 0 < retained <= prior_hold <= 5
    row.update(
        ceiling_usd=f"{retained:.2f}",
        state="terminal_closed_sdk_holds_refined_native_hold_unchanged",
        reconciliation="All closed SDK lifetimes plus300seconds at EACH end, unchanged full native-stage hold,0.10margin/upward quarter-dollar rounding. See "
        + args.proof.resolve().relative_to(EXPERIMENT).as_posix(),
    )
    released = prior_hold - retained
    ledger.update(
        reserved_upper_bound_usd=f"{held - released:.2f}",
        unallocated_usd=f"{Decimal(200) - held + released:.2f}",
        last_updated_at=datetime.now(UTC).isoformat(),
    )
    ledger["current_summary"] = (
        f"200USD authorized/{ledger['reserved_upper_bound_usd']}USD conservative holds/{ledger['unallocated_usd']}USD unallocated. Refined closed holds for {args.number}; other campaign states and allowances unchanged. No invoice/credits or future campaign funding inferred."
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    record = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": args.number,
        "applied": args.apply,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "source_archive_manifest_sha256": manifest_hash,
        "source_claim_sha256": digest(claim_raw),
        "source_runtime_identity_sha256": digest(runtime_raw),
        "fresh_cleanup_sha256": digest(cleanup_raw),
        "terminal": terminal,
        "checked_originals": checked,
        "closed_sdk_sessions": clocks,
        "sdk_resource_upper_bound_usd": str(upper),
        "unchanged_full_native_stage_hold_usd": str(native_hold),
        "margin_usd": "0.10",
        "rounding": "upward_to_0.25USD",
        "prior_hold_usd": f"{prior_hold:.2f}",
        "previous_unused_proof_sha256": previous_unused_hash,
        "runtime_round": args.runtime_round,
        "retained_usd": f"{retained:.2f}",
        "released_usd": f"{released:.2f}",
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "aggregate_held_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "new_campaign_full_reservation_unchanged": "5.00",
        "actual_provider_invoice_usd": None,
        "credits_assumed": False,
    }
    args.proof.write_text(json.dumps(record, indent=2) + "\n")
    if args.apply:
        assert ledger_path.read_bytes() == before
        ledger_path.write_bytes(after)
    print(
        json.dumps(
            {
                k: v
                for k, v in record.items()
                if k not in {"checked_originals", "closed_sdk_sessions"}
            }
        )
    )


if __name__ == "__main__":
    main()
