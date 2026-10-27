"""Conservative original-bound cost of the completed single setup session.

Operator accounting only. Reuses the tested full-lifetime price helper and the
unchanged unused-stage proof; does not reduce a new campaign's $5 reservation.
"""

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/070"))
from closed_session_bound import closed_session_bound  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.proof.exists()
    private = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
    archive = private / "archives/211"
    readback = json.loads((archive / "independent-readback.json").read_text())
    rows = {
        row["path"]: row
        for row in json.loads((archive / "sealed-manifest.json").read_text())["files"]
    }
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == digest(
        (archive / "sealed-manifest.json").read_bytes()
    )

    def original(name):
        raw = (archive / "files" / name).read_bytes()
        assert digest(raw) == rows[name]["sha256"] and len(raw) == rows[name]["bytes"]
        return json.loads(raw)

    pipeline, setup = original("pipeline.json"), original("setup-raw/result.json")
    assert pipeline["status"] == "rejected" and pipeline["operator_interventions"] == 0
    assert [(row["name"], row["status"]) for row in pipeline["stages"]] == [
        ("preparation", "completed"),
        ("setup", "rejected"),
    ]
    assert (
        setup["status"] == "worker_blocked"
        and setup["reference_tests"] == setup["reference_test_requests"] == 0
    )
    assert original("setup-raw/outcome.json")["disposition"] == "blocked"
    assert {name for name in rows if name.endswith("/sandbox-claim.json")} == {
        "setup-raw/sandbox-claim.json"
    }
    claim, clean = original("setup-raw/sandbox-claim.json"), original("setup-raw/cleanup.json")
    assert claim["state"] == "created" and claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    assert clean["passed"] and not clean["remaining"] and not clean.get("creation_uncertain")
    assert (
        len(clean["sandboxes"]) == 1
        and clean["sandboxes"][0]["id"] == claim["id"]
        and clean["sandboxes"][0]["deleted"] is True
    )
    fresh = json.loads((archive / "fresh-provider-cleanup.json").read_text())
    assert (
        fresh["complete"]
        and fresh["original_all_cleanup_passed"]
        and fresh["all_original_sdk_claim_ids_checked"]
        and fresh["fresh_original_ids_absent"]
        and not fresh["sandboxes"]
    )
    assert (
        fresh["owners"] == [claim["owner"]]
        and fresh["source_archive_manifest_sha256"] == readback["source_manifest_sha256"]
    )
    proof_root = Path(__file__).parent
    previous = json.loads((proof_root / "unused-211-applied.json").read_text())
    assert previous["applied"] and len(previous["records"]) == 1
    old = previous["records"][0]
    assert (
        old["campaign"] == 211
        and old["dispatched_stages"] == ["setup"]
        and old["retained_full_dispatched_stage_hold_usd"] == "1.00"
    )
    assert old["terminal"]["state"] == "SUCCEEDED" and old["terminal"]["terminal"]
    submission = json.loads((private / "launch/211-submission.json").read_text())
    payload = private / "launch/211-payload"
    assert (
        digest((payload / "biotasks.tar").read_bytes())
        == submission["inputs"]["files"]["biotasks.tar"]
    )
    identity = json.loads((proof_root / "runtime-identity.json").read_text())
    frozen = json.loads((proof_root / "freeze-211.json").read_text())
    assert frozen["input_revision"] == submission["factory_revision"]
    with tarfile.open(payload / "biotasks.tar") as source:
        actual = {
            row.name: hashlib.file_digest(source.extractfile(row), "sha256").hexdigest()
            for row in source
            if row.isfile()
        }
    assert actual == {**identity["runtime_files"], **frozen["source_assets"]}
    config = original("setup-raw/configuration.json")
    assert config["campaign"] == claim["owner"]
    assert (config["cleanup_seconds"], config["setup_seconds"], config["max_tests"]) == (
        300,
        1800,
        2,
    )
    original_config = (payload / "campaign-config.json").read_bytes()
    assert digest(original_config) == submission["inputs"]["files"]["campaign-config.json"]
    assert json.loads(original_config)["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }

    # The admitted creator starts its result clock before remote creation and
    # ends it after successful cleanup. The104AST proof preserves that creator
    # and every pre-existing setup method; this run dispatched no new method.
    assert (
        identity["runtime_files"]["experiments/19-repo2rlenv-notebook-pilot/run_reference_setup.py"]
        == "cfeefdda2dc0f2ba4a62618e9202b6ef3af038a48ff78a35337e1567fcfe25f3"
    )
    priced = closed_session_bound(setup, pipeline, [], 300)
    retained = (
        (Decimal(priced["resource_upper_bound_usd"]) + Decimal("0.10")) / Decimal("0.25")
    ).to_integral_value(rounding=ROUND_CEILING) * Decimal("0.25")
    assert retained == Decimal("0.25")
    ledger_path = EXPERIMENT / "aggregate-budget.json"
    before = ledger_path.read_bytes()
    ledger = json.loads(before)
    row = next(
        row for row in ledger["reservations"] if row["scope"].startswith("autonomous-panel-211:")
    )
    assert (
        row["ceiling_usd"] == "1.00"
        and row["state"] == "unused_stage_allowances_released_used_holds_unchanged"
    )
    assert sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"]) == Decimal(
        ledger["reserved_upper_bound_usd"]
    )
    released = Decimal("1.00") - retained
    row.update(
        ceiling_usd=f"{retained:.2f}",
        state="terminal_closed_setup_lifetime_reconciled",
        reconciliation="Original single setup claim/deletion, source payload, terminal/root and fresh-ID/owner absence verified. Complete resource clock plus300seconds at both ends,0.10USDmargin and upward quarter-dollar rounding; no invoice or credits. See "
        + args.proof.name,
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
        "campaign": 211,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "source_manifest_sha256": readback["source_manifest_sha256"],
        "original_source_hashes": {
            name: rows[name]["sha256"]
            for name in (
                "pipeline.json",
                "setup-raw/result.json",
                "setup-raw/configuration.json",
                "setup-raw/sandbox-claim.json",
                "setup-raw/cleanup.json",
            )
        },
        "fresh_cleanup_sha256": digest((archive / "fresh-provider-cleanup.json").read_bytes()),
        "preceding_unused_stage_proof_sha256": digest(
            (proof_root / "unused-211-applied.json").read_bytes()
        ),
        "source_ledger_sha256": digest(before),
        "result_ledger_sha256": digest(after),
        "closed_session": priced,
        "retained_usd": f"{retained:.2f}",
        "released_usd": f"{released:.2f}",
        "aggregate_held_usd": ledger["reserved_upper_bound_usd"],
        "unallocated_usd": ledger["unallocated_usd"],
        "new_campaign_reservation_unchanged": "5.00",
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
                if key not in ("original_source_hashes", "closed_session")
            }
        )
    )


if __name__ == "__main__":
    main()
