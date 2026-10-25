"""Bound an archived four-sandbox SDK-only run without assuming serial lifetimes.

This narrow additional profile leaves the seven-owner/native auditor unchanged.
Every sandbox is priced for the entire approved campaign plus cleanup, at once.
Only the already-reviewed controller/setup implementation is admitted. No credit,
short observed duration or provider invoice is inferred.
"""

import argparse
import hashlib
import json
import tarfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

EXPERIMENT = "experiments/19-repo2rlenv-notebook-pilot/"
CONTROLLER = "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188"
FOLDERS = ["setup-raw", "replay", "materialization-raw", "grading"]
RATE = 4 * Decimal("0.0504") + 8 * Decimal("0.0162") + 10 * Decimal("0.000108")


def admitted_implementation(sources):
    """Exact creator/session pairs with identical creation and cleanup logic.

    The later creator only adds static source-operation context to the worker.
    The newest pair only adds fail-closed network-result checks and catches a
    typed export-repair rejection. None changes resource creation or cleanup.
    The earlier exact triple predates the full-budget guard refactor and one
    source-path argument to dependency inspection; its creator is byte-identical.
    Every pair must also have passed its preceding lifetime auditor.
    """
    assert set(sources) == {"run_autonomous.py", "run_reference_setup.py", "reference_setup.py"}
    if sources == {
        "run_autonomous.py": "972b6315182a86988dab558ec42e63891d2dd8a380ae224253d209f476db3b12",
        "run_reference_setup.py": "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
        "reference_setup.py": "a73ff8ccfbc5281a51ba55817316f33d8d3398d4227c4218f6bf0e553c3b2c83",
    }:
        return dict(sources)
    assert sources["run_autonomous.py"] == (
        "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188"
    )
    assert (sources["run_reference_setup.py"], sources["reference_setup.py"]) in {
        (
            "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
            "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
        ),
        (
            "fc83bf2ecd9f201b4bfd8c47cb07740619d09c66fc8df5a37435eb95af5b2d0b",
            "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
        ),
        (
            "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8",
            "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7",
        ),
    }
    return dict(sources)


def terminal_state(pipeline):
    """Match a final grading outcome to its required typed host state."""
    stages = pipeline["stages"]
    assert [s["name"] for s in stages] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
    ]
    assert all(s["status"] == "completed" for s in stages[:-1])
    if pipeline["status"] == "rejected":
        assert stages[-1]["status"] == "rejected"
        return "SUCCEEDED"
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline.get("failed_stage") == "grading" and stages[-1]["status"] == "incomplete"
    return "FAILED"


def audit_shape(pipeline, claims, cleanup):
    terminal_state(pipeline)
    stages = pipeline["stages"]
    assert pipeline["started"] <= stages[0]["started"]
    assert stages[-1]["finished"] <= pipeline["finished"]
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert all(s["started"] <= s["finished"] for s in stages)
    assert all(a["finished"] <= b["started"] for a, b in zip(stages, stages[1:], strict=False))
    assert len(claims) == len(cleanup["owners"]) == 4
    assert len({c["id"] for c in claims}) == 4
    assert len({c["owner"] for c in claims}) == 4
    assert set(cleanup["owners"]) == {c["owner"] for c in claims}
    for c in claims:
        assert c["state"] == "created"
        assert c["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["fresh_original_ids_absent"] and not cleanup["sandboxes"]
    # Four complete profiles for 7500 seconds, irrespective of overlap.
    bound = len(claims) * RATE * Decimal(7500) / Decimal(3600)
    assert bound == Decimal("2.769000") < Decimal("3.00")
    return bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.proof.exists()
    before = args.ledger.read_bytes()
    ledger = json.loads(before)
    assert sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"]) == Decimal(
        ledger["reserved_upper_bound_usd"]
    )
    archive = args.private_root / f"archives/{args.number:03}"
    manifest_raw = (archive / "sealed-manifest.json").read_bytes()
    manifest_hash = hashlib.sha256(manifest_raw).hexdigest()
    manifest = {r["path"]: r for r in json.loads(manifest_raw)["files"]}
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == manifest_hash
    root = json.loads((archive / "root-evidence/readback.json").read_text())
    assert root["all_manifest_files_hash_size_mode_verified"]
    checked = {}

    def original(name):
        raw = (archive / "files" / name).read_bytes()
        assert len(raw) == manifest[name]["bytes"]
        assert hashlib.sha256(raw).hexdigest() == manifest[name]["sha256"]
        checked[name] = manifest[name]["sha256"]
        return json.loads(raw)

    launch = args.private_root / "launch"
    submission_raw = (launch / f"{args.number:03}-submission.json").read_bytes()
    submission = json.loads(submission_raw)
    payload = launch / f"{args.number:03}-payload"
    frozen = {}
    for name in ["campaign-config.json", "biotasks.tar"]:
        raw = (payload / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == submission["inputs"]["files"][name]
        frozen[name] = hashlib.sha256(raw).hexdigest()
    config = json.loads((payload / "campaign-config.json").read_text())
    assert config["campaign_seconds"] == 7200 and config["cleanup_seconds"] == 300
    assert Decimal(config["daytona_budget_usd"]) == Decimal("5.00")
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }
    source_hashes = {}
    with tarfile.open(payload / "biotasks.tar") as source:
        for name in ["run_autonomous.py", "run_reference_setup.py", "reference_setup.py"]:
            source_hashes[name] = hashlib.sha256(
                source.extractfile(EXPERIMENT + name).read()
            ).hexdigest()
    admitted_implementation(source_hashes)
    # This reviewed SDK path creates from an image once per recorded stage,
    # without persistent snapshot creation or native Harbor dispatch at this prefix.
    pipeline = original("pipeline.json")
    clean = json.loads((archive / "fresh-provider-cleanup.json").read_text())
    assert clean["source_archive_manifest_sha256"] == manifest_hash
    assert clean["source_configuration_sha256"] == frozen["campaign-config.json"]
    assert {n for n in manifest if n.endswith("/sandbox-claim.json")} == {
        f + "/sandbox-claim.json" for f in FOLDERS
    }
    assert not any(n.startswith("native/") for n in manifest)
    claims = [original(f + "/sandbox-claim.json") for f in FOLDERS]
    bound = audit_shape(pipeline, claims, clean)
    assert {r["path"] for r in clean["original_cleanup_evidence"]} == {
        f + "/cleanup.json" for f in FOLDERS
    }
    for folder, claim in zip(FOLDERS, claims, strict=True):
        stage = original(folder + "/configuration.json")
        assert stage["campaign"] == claim["owner"]
        assert claim["owner"].startswith(config["campaign"] + "-")
        cleanup = original(folder + "/cleanup.json")
        assert cleanup["passed"] and not cleanup["remaining"]
        assert not cleanup.get("creation_uncertain")
        assert len(cleanup["sandboxes"]) == 1
        box = cleanup["sandboxes"][0]
        assert box["id"] == claim["id"] and box["deleted"]
        assert {k: box[k] for k in ["cpu", "memory", "disk"]} == claim["resources"]
    observations = [
        json.loads(p.read_text())
        for p in (launch / "typed-observations").glob(f"{args.number:03}-*.json")
    ]
    terminal = max(observations, key=lambda r: r["observed_at"])
    assert terminal["terminal"] and terminal["state"] == terminal_state(pipeline)
    assert terminal["claim_sha256"] == hashlib.sha256(submission_raw).hexdigest()
    row = next(
        r
        for r in ledger["reservations"]
        if r["scope"].startswith(f"autonomous-panel-{args.number:03}:")
    )
    assert row["ceiling_usd"] == "4.00"
    row.update(
        ceiling_usd="3.00",
        state="terminal_sdk_only_all_lifetimes_bound_reconciled",
        reconciliation="Four verified deleted SDK sandboxes, each priced for7500s even if all overlap; retain3USD against2.769USD. No snapshot/native dispatch or credits assumed. See "
        + args.proof.relative_to(args.ledger.parent).as_posix(),
    )
    held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    ceiling = Decimal(ledger["ceiling_before_credits"])
    assert held == Decimal(json.loads(before)["reserved_upper_bound_usd"]) - 1
    ledger.update(reserved_upper_bound_usd=f"{held:.2f}", unallocated_usd=f"{ceiling - held:.2f}")
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "campaign": args.number,
        "profile": "sdk_only_four_full_lifetimes_no_serial_assumption",
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_ledger_sha256": hashlib.sha256(before).hexdigest(),
        "result_ledger_sha256": hashlib.sha256(after).hexdigest(),
        "source_manifest_sha256": manifest_hash,
        "checked_originals": checked,
        "frozen_implementation_sha256": source_hashes,
        "terminal": terminal,
        "cleanup_observed_at": clean["observed_at"],
        "all_original_ids_absent": True,
        "all_original_owners_absent": True,
        "original_limits_changed": False,
        "rates_source": "https://www.daytona.io/pricing",
        "billing_source": "https://www.daytona.io/docs/billing/",
        "hourly_full_profile_usd": str(RATE),
        "priced_sandboxes": 4,
        "seconds_each": 7500,
        "resource_upper_bound_usd": str(bound),
        "retained_usd": "3.00",
        "released_usd": "1.00",
        "actual_invoice_usd": None,
        "credits_assumed": False,
        "aggregate_held_usd": f"{held:.2f}",
        "unallocated_usd": f"{ceiling - held:.2f}",
    }
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if args.apply:
        assert args.ledger.read_bytes() == before
        args.ledger.write_bytes(after)
    print(
        json.dumps(
            {
                k: v
                for k, v in proof.items()
                if k not in {"checked_originals", "frozen_implementation_sha256", "terminal"}
            }
        )
    )


if __name__ == "__main__":
    main()
