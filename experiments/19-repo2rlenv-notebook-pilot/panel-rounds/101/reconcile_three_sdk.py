"""Reprice closed three-SDK prefixes, preserving their original failed outcomes.

Only two reviewed controller profiles are admitted. Every sandbox is charged for
its entire recorded lifetime plus 300 seconds at each end. This is a conservative
resource bound, not an invoice, a credit or permission to weaken a new reservation.
"""

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "070"))
from closed_session_bound import RATE, closed_session_bound  # noqa: E402

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
FOLDERS = ("setup-raw", "replay", "materialization-raw")
SOURCES = {
    "underfunded_before_grading": {
        "run_autonomous.py": "972b6315182a86988dab558ec42e63891d2dd8a380ae224253d209f476db3b12",
        "run_reference_setup.py": "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
        "reference_setup.py": "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
        "daytona_session.py": "9dee33c95f0fe76c79ca4bff5017223912401f539ce999e29ab5b754fb2682b0",
    },
    "construction_incomplete": {
        "run_autonomous.py": "90037510e244c3012fd2024a092f1d327028b2fa6f2c62f42018b31a78623b4b",
        "run_reference_setup.py": "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8",
        "reference_setup.py": "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7",
        "daytona_session.py": "6b9da0f5bf020dd9330f80a80586b0b0cca494c80576b2543416b636fb99751a",
    },
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def audit_profile(pipeline, sources, budget):
    names = [row["name"] for row in pipeline["stages"]]
    assert names == ["preparation", "setup", "replay", "specification", "construction"]
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline["daytona_reserved_usd"] == 3
    assert all(row["status"] == "completed" for row in pipeline["stages"][:-1])
    if pipeline["failed_stage"] == "grading":
        profile = "underfunded_before_grading"
        assert pipeline["stages"][-1]["status"] == "completed" and budget == "3.00"
        assert not pipeline.get("quality_repair")
    else:
        profile = "construction_incomplete"
        assert pipeline["failed_stage"] == "construction" and budget == "5.00"
        assert pipeline["stages"][-1]["status"] == "incomplete"
        repair = pipeline["quality_repair"]
        assert repair["kind"] == "specification_review" and repair["allowance_consumed"]
        assert repair["target"] == "task_specification" and repair["validation_status"] == "ready"
    assert sources == SOURCES[profile], "Unknown or crosswired source family"
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert all(
        a["finished"] <= b["started"]
        for a, b in zip(pipeline["stages"], pipeline["stages"][1:], strict=False)
    )
    return profile


def retained(upper):
    assert upper.is_finite() and Decimal(0) < upper < Decimal(1)
    return ((upper + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numbers", type=int, nargs="+")
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.proof.exists() and len(set(args.numbers)) == len(args.numbers)
    before = args.ledger.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"])
    records = []
    for number in args.numbers:
        archive = args.private_root / f"archives/{number}"
        manifest_raw = (archive / "sealed-manifest.json").read_bytes()
        manifest_hash = digest(manifest_raw)
        entries = {r["path"]: r for r in json.loads(manifest_raw)["files"]}
        readback = json.loads((archive / "independent-readback.json").read_text())
        assert (
            readback["all_files_download_verified"]
            and readback["source_manifest_sha256"] == manifest_hash
        )
        assert json.loads((archive / "root-evidence/readback.json").read_text())[
            "all_manifest_files_hash_size_mode_verified"
        ]
        checked = {}

        def original(name, archive=archive, entries=entries, checked=checked):
            raw = (archive / "files" / name).read_bytes()
            assert len(raw) == entries[name]["bytes"] and digest(raw) == entries[name]["sha256"]
            checked[name] = digest(raw)
            return json.loads(raw)

        launch = args.private_root / "launch"
        claim_raw = (launch / f"{number}-submission.json").read_bytes()
        claim = json.loads(claim_raw)
        status = json.loads((archive / "bootstrap-evidence/job-state-latest.json").read_text())
        assert status["state"] == "FAILED" and status["terminal"]
        assert status["source_claim_sha256"] == digest(claim_raw)
        payload = launch / f"{number}-payload"
        config_raw = (payload / "campaign-config.json").read_bytes()
        assert digest(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
        config = json.loads(config_raw)
        assert config["campaign_seconds"] == 7200 and config["cleanup_seconds"] == 300
        assert config["task_policy"]["sandbox"] == {
            "cpus": 4,
            "memory_gib": 8,
            "disk_gib": 10,
            "gpu": False,
        }
        with (payload / "biotasks.tar").open("rb") as stream:
            assert (
                hashlib.file_digest(stream, "sha256").hexdigest()
                == claim["inputs"]["files"]["biotasks.tar"]
            )
        pipeline = original("pipeline.json")
        profile = (
            "underfunded_before_grading"
            if pipeline["failed_stage"] == "grading"
            else "construction_incomplete"
        )
        with tarfile.open(payload / "biotasks.tar") as source:
            sources = {
                name: digest(source.extractfile(PREFIX + name).read()) for name in SOURCES[profile]
            }
        audit_profile(pipeline, sources, config["daytona_budget_usd"])
        assert {name for name in entries if name.endswith("/sandbox-claim.json")} == {
            f + "/sandbox-claim.json" for f in FOLDERS
        }
        assert not any(name.startswith("native/") for name in entries)
        clean_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
        clean = json.loads(clean_raw)
        assert (
            clean["complete"]
            and clean["original_all_cleanup_passed"]
            and clean["fresh_original_ids_absent"]
            and not clean["sandboxes"]
        )
        assert clean["source_archive_manifest_sha256"] == manifest_hash and clean[
            "source_configuration_sha256"
        ] == digest(config_raw)
        assert {r["path"] for r in clean["original_cleanup_evidence"]} == {
            f + "/cleanup.json" for f in FOLDERS
        }
        lifetimes, owners, ids = [], [], []
        for folder in FOLDERS:
            created = original(folder + "/sandbox-claim.json")
            stage = original(folder + "/configuration.json")
            cleanup = original(folder + "/cleanup.json")
            assert created["state"] == "created" and created["resources"] == {
                "cpu": 4,
                "memory": 8,
                "disk": 10,
            }
            assert stage["campaign"] == created["owner"] and created["owner"].startswith(
                config["campaign"] + "-"
            )
            assert (
                cleanup["passed"]
                and not cleanup.get("remaining")
                and not cleanup.get("creation_uncertain")
            )
            assert cleanup["sandboxes"] == [
                {"id": created["id"], "cpu": 4, "memory": 8, "disk": 10, "deleted": True}
            ]
            owners.append(created["owner"])
            ids.append(created["id"])
            session = original(folder + "/result.json")
            enclosing = next(
                r
                for r in pipeline["stages"]
                if r["name"]
                == {
                    "setup-raw": "setup",
                    "replay": "replay",
                    "materialization-raw": "construction",
                }[folder]
            )
            assert (
                enclosing["started"]
                <= session["started"]
                < session["finished"]
                <= enclosing["finished"]
            )
            lifetimes.append({"stage": folder, **closed_session_bound(session, pipeline, [], 300)})
        assert len(set(ids)) == len(set(owners)) == 3 and set(owners) == set(clean["owners"])
        upper = sum(Decimal(r["resource_upper_bound_usd"]) for r in lifetimes)
        keep = retained(upper)
        row = next(
            r
            for r in ledger["reservations"]
            if r["scope"].startswith(f"autonomous-panel-{number}:")
        )
        assert row["ceiling_usd"] == "3.00" and row["state"] in {
            "terminal_conservative_hold_unreconciled",
            "unused_stage_allowances_released_used_holds_unchanged",
        }
        row.update(
            ceiling_usd=f"{keep:.2f}",
            state="terminal_three_sdk_closed_lifetimes_refined",
            reconciliation="Exact original three-SDK prefix, known source family, terminal state, all closed lifetimes with300seconds at each end, original and fresh cleanup; add0.10USD and round upward to0.25USD. No invoice, credits or outcome changes. See "
            + args.proof.relative_to(args.ledger.parent).as_posix(),
        )
        records.append(
            {
                "campaign": number,
                "profile": profile,
                "sources": sources,
                "checked_originals": checked,
                "manifest_sha256": manifest_hash,
                "fresh_cleanup_sha256": digest(clean_raw),
                "terminal_sha256": digest(
                    (archive / "bootstrap-evidence/job-state-latest.json").read_bytes()
                ),
                "lifetimes": lifetimes,
                "upper_usd": str(upper),
                "retained_usd": f"{keep:.2f}",
                "released_usd": f"{Decimal(3) - keep:.2f}",
            }
        )
    after_held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    assert after_held == held - sum(Decimal(r["released_usd"]) for r in records)
    ledger.update(
        reserved_upper_bound_usd=f"{after_held:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - after_held:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "profile_helper_sha256": digest(
            (Path(__file__).resolve().parents[1] / "070/closed_session_bound.py").read_bytes()
        ),
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "records": records,
        "aggregate_held_usd": f"{after_held:.2f}",
        "unallocated_usd": ledger["unallocated_usd"],
        "rate_usd_per_hour": str(RATE),
        "new_resources_or_models": 0,
        "scientific_outcomes_changed": False,
        "actual_provider_invoice_usd": None,
        "free_credits_assumed": False,
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if args.apply:
        assert args.ledger.read_bytes() == before
        args.ledger.write_bytes(after)
    print(json.dumps({k: v for k, v in proof.items() if k != "records"}))


if __name__ == "__main__":
    main()
