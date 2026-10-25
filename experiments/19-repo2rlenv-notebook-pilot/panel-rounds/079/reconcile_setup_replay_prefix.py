"""Price a known terminal two-SDK setup/replay prefix; keep other profiles separate."""

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "070"))
from closed_session_bound import RATE, closed_session_bound  # noqa: E402

FOLDERS = ("setup-raw", "replay")
# Reviewed exact source family: one image-created SDK sandbox per stage; the
# controller reaches only preparation/setup/replay, before review/native work.
# Session clocks begin before create and finish after successful owner cleanup.
SOURCES = {
    "run_autonomous.py": "90037510e244c3012fd2024a092f1d327028b2fa6f2c62f42018b31a78623b4b",
    "run_reference_setup.py": "853829d72083c806383e7c3c0acc2d0e3edb4800027e58ae5789e936fc346a6d",
    "reference_setup.py": "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7",
    "run_reference_replay.py": "2f67809b6be3d3463aece4c5a84f3dc495f177c89d5b85e3d709e3c816510d08",
    "preflight.py": "b9c0facbfded6d72a46cd927393417f88eeda8e092744d84a85a54c4c8bd3003",
    "daytona_session.py": "6b9da0f5bf020dd9330f80a80586b0b0cca494c80576b2543416b636fb99751a",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(pipeline, sources, claims, sessions, clean):
    assert sources == SOURCES
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline["failed_stage"] == "replay" and not pipeline.get("quality_repair")
    stages = pipeline["stages"]
    assert [s["name"] for s in stages] == ["preparation", "setup", "replay"]
    assert [s["status"] for s in stages] == ["completed", "completed", "incomplete"]
    assert pipeline["started"] <= stages[0]["started"]
    assert stages[-1]["finished"] <= pipeline["finished"]
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert all(s["started"] <= s["finished"] for s in stages)
    assert all(a["finished"] <= b["started"] for a, b in zip(stages, stages[1:], strict=False))
    assert set(claims) == set(sessions) == set(FOLDERS)
    assert len({c["id"] for c in claims.values()}) == 2
    assert len({c["owner"] for c in claims.values()}) == 2
    assert set(clean["owners"]) == {c["owner"] for c in claims.values()}
    assert clean["complete"] and clean["original_all_cleanup_passed"]
    assert clean["fresh_original_ids_absent"] and not clean["sandboxes"]
    for claim in claims.values():
        assert claim["state"] == "created"
        assert claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    coarse = 2 * RATE * 7500 / 3600
    assert coarse == Decimal("1.384500") < 2
    records = {
        folder: closed_session_bound(sessions[folder], pipeline, [], 300) for folder in FOLDERS
    }
    upper = sum(Decimal(r["resource_upper_bound_usd"]) for r in records.values())
    assert 0 < upper < 1
    return coarse, upper, records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("number", type=int)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--proof", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    assert not a.proof.exists()
    archive = a.private_root / f"archives/{a.number:03}"
    raw = (archive / "sealed-manifest.json").read_bytes()
    manifest_hash = digest(raw)
    manifest = {r["path"]: r for r in json.loads(raw)["files"]}
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == manifest_hash
    assert json.loads((archive / "root-evidence/readback.json").read_text())[
        "all_manifest_files_hash_size_mode_verified"
    ]
    checked = {}

    def original(name):
        data = (archive / "files" / name).read_bytes()
        assert len(data) == manifest[name]["bytes"]
        assert digest(data) == manifest[name]["sha256"]
        checked[name] = digest(data)
        return json.loads(data)

    launch = a.private_root / "launch"
    claim_raw = (launch / f"{a.number:03}-submission.json").read_bytes()
    submission = json.loads(claim_raw)
    payload = launch / f"{a.number:03}-payload"
    for name in ("campaign-config.json", "biotasks.tar"):
        assert digest((payload / name).read_bytes()) == submission["inputs"]["files"][name]
    config = json.loads((payload / "campaign-config.json").read_text())
    assert config["campaign_seconds"] == 7200 and config["cleanup_seconds"] == 300
    assert config["daytona_budget_usd"] == "5.00"
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }
    with tarfile.open(payload / "biotasks.tar") as packet:
        sources = {
            name: digest(
                packet.extractfile("experiments/19-repo2rlenv-notebook-pilot/" + name).read()
            )
            for name in SOURCES
        }
    clean_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
    clean = json.loads(clean_raw)
    assert clean["source_archive_manifest_sha256"] == manifest_hash
    assert clean["source_configuration_sha256"] == digest(
        (payload / "campaign-config.json").read_bytes()
    )
    assert {n for n in manifest if n.endswith("/sandbox-claim.json")} == {
        f + "/sandbox-claim.json" for f in FOLDERS
    }
    assert not any(
        n.startswith(("native/", "specification/", "materialization", "grading")) for n in manifest
    )
    assert {r["path"] for r in clean["original_cleanup_evidence"]} == {
        f + "/cleanup.json" for f in FOLDERS
    }
    claims, sessions = {}, {}
    for folder in FOLDERS:
        claims[folder] = original(folder + "/sandbox-claim.json")
        stage = original(folder + "/configuration.json")
        assert stage["campaign"] == claims[folder]["owner"]
        assert stage["campaign"].startswith(config["campaign"] + "-")
        cleanup = original(folder + "/cleanup.json")
        assert (
            cleanup["passed"] and not cleanup["remaining"] and not cleanup.get("creation_uncertain")
        )
        assert cleanup["sandboxes"] == [
            {"id": claims[folder]["id"], "cpu": 4, "memory": 8, "disk": 10, "deleted": True}
        ]
        sessions[folder] = original(folder + "/result.json")
    pipeline = original("pipeline.json")
    coarse, upper, records = audit(pipeline, sources, claims, sessions, clean)
    observations = [
        json.loads(p.read_text())
        for p in (launch / "typed-observations").glob(f"{a.number:03}-*.json")
    ]
    terminal = max(observations, key=lambda r: r["observed_at"])
    assert terminal["terminal"] and terminal["state"] == "FAILED"
    assert terminal["claim_sha256"] == digest(claim_raw)
    before = a.ledger.read_bytes()
    ledger = json.loads(before)
    held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
    assert held == Decimal(ledger["reserved_upper_bound_usd"])
    row = next(
        r
        for r in ledger["reservations"]
        if r["scope"].startswith(f"autonomous-panel-{a.number:03}:")
    )
    assert (
        row["ceiling_usd"] == "2.00"
        and row["state"] == "unused_stage_allowances_released_used_holds_unchanged"
    )
    row.update(
        ceiling_usd="1.00",
        state="terminal_two_sdk_closed_lifetimes_reconciled",
        reconciliation="Both complete original SDK sessions priced at full resources plus300seconds at EACH end, against exact reviewed source family and fresh cleanup. Retain1USD; no invoices or credits assumed. See "
        + a.proof.relative_to(a.ledger.parent).as_posix(),
    )
    ledger.update(
        reserved_upper_bound_usd=f"{held - 1:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held + 1:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = dict(
        observed_at=datetime.now(UTC).isoformat(),
        campaign=a.number,
        applied=a.apply,
        helper_sha256=digest(Path(__file__).read_bytes()),
        clock_helper_sha256=digest(
            Path(__file__).resolve().parents[1].joinpath("070/closed_session_bound.py").read_bytes()
        ),
        source_manifest_sha256=manifest_hash,
        source_ledger_sha256=digest(before),
        result_ledger_sha256=digest(after),
        checked_originals=checked,
        frozen_implementation_sha256=sources,
        fresh_cleanup_sha256=digest(clean_raw),
        terminal=terminal,
        coarse_full_lifetimes_bound_usd=str(coarse),
        resource_upper_bound_usd=str(upper),
        records=records,
        retained_usd="1.00",
        released_usd="1.00",
        aggregate_held_usd=ledger["reserved_upper_bound_usd"],
        unallocated_usd=ledger["unallocated_usd"],
        actual_provider_invoice_usd=None,
        credits_assumed=False,
        original_execution_status_changed=False,
    )
    a.proof.write_text(json.dumps(proof, indent=2) + "\n")
    if a.apply:
        assert a.ledger.read_bytes() == before
        a.ledger.write_bytes(after)
    print(
        json.dumps(
            {
                k: v
                for k, v in proof.items()
                if k
                not in {"checked_originals", "frozen_implementation_sha256", "records", "terminal"}
            }
        )
    )


if __name__ == "__main__":
    main()
