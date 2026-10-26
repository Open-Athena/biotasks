"""Price explicit terminal SDK prefixes; keep older/native profiles separate."""

import argparse
import hashlib
import importlib.util
import json
import sys
import tarfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "070"))
from closed_session_bound import RATE, closed_session_bound  # noqa: E402

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "factory-checks/native-preparation-deadline")
)
from audit_prefix import audit_no_dispatch, frozen_sources  # noqa: E402

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
GRADING_SOURCES = {
    **SOURCES,
    # Earlier bounded-network implementation; image creation/cleanup is identical.
    "run_reference_setup.py": "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8",
}
WORKSPACE_GRADING_SOURCES = {
    **SOURCES,
    # Reviewed workspace isolation and cumulative setup-budget fixes. These
    # retain one image-created sandbox per stage and the same cleanup boundary.
    "run_reference_setup.py": "d69dd179b16f1ea16b385be6b838a2f88d21e57cfc5e6bf3701e5e8e36af5500",
    "reference_setup.py": "77a99214c1c23a5b8208830956a086d0544e5641fb95ede652192017c99cdd4e",
}
CURRENT_SPECIFICATION_SOURCES = {
    **WORKSPACE_GRADING_SOURCES,
    # Same image creation/cleanup, with source-bound identical upload recovery.
    "run_reference_setup.py": "5349631f69d5426ce822882f2bc5df5ae3724efe7fbcd0ee0979681187472c30",
    "upload_transfer.py": "816875df9e886e9499b29c28496df2bed9218fa24b98a64eb4343c1e3f48064c",
}
COMPARISON_REPAIR_SOURCES = {
    **CURRENT_SPECIFICATION_SOURCES,
    # Reviewed direct diagnosis followed by exactly one fresh grading session.
    "run_notebook_grader.py": "714a3702b99cd64c32a9c3fd2354e5c4a74a8a47304c24df6ef230beaea5ce4c",
    "grading_session.py": "eed7737caa2e3efc8503e4186661bfe9039dec5f5f1f7c98afebf06ced36b540",
    "comparison_repair.py": "0d54551fc45b29ea9033509ebc4154c87e1bae94f0ed6a2d12b20d14ec2dabbe",
    "question_repair.py": "ca834e99dafb2c793b1e955363c3e2d675745573b54e46fa62901c0aa46ddb39",
}
LEGACY_REPLAY_SOURCES = {
    **SOURCES,
    "run_autonomous.py": "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188",
    "run_reference_setup.py": "fc83bf2ecd9f201b4bfd8c47cb07740619d09c66fc8df5a37435eb95af5b2d0b",
    "reference_setup.py": "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
    "preflight.py": "e6f49af20e00306d137a3027ee7e29a5369f93fbd82530925d071601b5afd77b",
}
LEGACY_SPECIFICATION_SOURCES = {
    **GRADING_SOURCES,
    "run_autonomous.py": LEGACY_REPLAY_SOURCES["run_autonomous.py"],
}


def common_runtime():
    """Admit the complete tested candidate, never an arbitrary new source hash."""
    experiment = Path(__file__).resolve().parents[2]
    panel = experiment / "panel-rounds/101"
    source_proof = panel / "source-admission.json"
    helper = panel / "runtime_admission.py"
    assert (
        digest(helper.read_bytes())
        == json.loads(source_proof.read_text())["admission_helper_sha256"]
    )
    spec = importlib.util.spec_from_file_location("common_sdk_source_admission", helper)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    identity = panel / "runtime-identity.json"
    runtime = json.loads(identity.read_text())["runtime_files"]
    module.candidate_admission(experiment.parents[1], runtime)
    return runtime, {
        "source_admission_sha256": digest(source_proof.read_bytes()),
        "admission_helper_sha256": digest(helper.read_bytes()),
        "runtime_identity_sha256": digest(identity.read_bytes()),
    }


def check_common_payload(packet, config, runtime):
    """Every executable payload file must match that admitted common runtime."""
    prefix = "experiments/19-repo2rlenv-notebook-pilot/"
    assets = set()
    for key in ("seed_file", "notebook_file", "source_notices_file"):
        if config.get(key) is None:
            continue
        value = config[key]
        path = PurePosixPath(value)
        assert not path.is_absolute() and ".." not in path.parts and str(path) == value
        assets.add(prefix + value)
    actual, seen, present_assets = {}, set(), set()
    for member in packet.getmembers():
        if member.isdir():
            continue
        assert member.isfile() and member.name not in seen
        seen.add(member.name)
        if member.name in assets:
            present_assets.add(member.name)
        else:
            actual[member.name] = digest(packet.extractfile(member).read())
    assert present_assets == assets and actual == runtime, "Unadmitted executable payload"


def profile_config(profile):
    if profile in {"common_grading_rejection", "common_grading_failure"}:
        runtime, _ = common_runtime()
        sources = {
            name: runtime["experiments/19-repo2rlenv-notebook-pilot/" + name]
            for name in CURRENT_SPECIFICATION_SOURCES
        }
        return (
            (*FOLDERS, "materialization-raw", "grading"),
            ["preparation", "setup", "replay", "specification", "construction", "grading"],
            sources,
        )
    if profile == "current_comparison_repair_failure":
        return (
            (*FOLDERS, "materialization-raw", "grading", "grading-comparison-repair"),
            ["preparation", "setup", "replay", "specification", "construction", "grading"],
            COMPARISON_REPAIR_SOURCES,
        )
    if profile == "current_setup_rejection":
        return ("setup-raw",), ["preparation", "setup"], CURRENT_SPECIFICATION_SOURCES
    if profile == "setup_replay":
        return FOLDERS, ["preparation", "setup", "replay"], SOURCES
    if profile == "legacy_setup_replay":
        return FOLDERS, ["preparation", "setup", "replay"], LEGACY_REPLAY_SOURCES
    if profile == "legacy_specification_rejection":
        return (
            FOLDERS,
            ["preparation", "setup", "replay", "specification"],
            LEGACY_SPECIFICATION_SOURCES,
        )
    if profile == "current_specification_rejection":
        return (
            FOLDERS,
            ["preparation", "setup", "replay", "specification"],
            CURRENT_SPECIFICATION_SOURCES,
        )
    assert profile in {
        "grading",
        "workspace_grading",
        "current_grading_rejection",
        "current_grading_failure",
        "current_native_preparation_failure",
    }
    grading_sources = {
        "grading": GRADING_SOURCES,
        "workspace_grading": WORKSPACE_GRADING_SOURCES,
        "current_grading_rejection": CURRENT_SPECIFICATION_SOURCES,
        "current_grading_failure": CURRENT_SPECIFICATION_SOURCES,
        "current_native_preparation_failure": CURRENT_SPECIFICATION_SOURCES,
    }
    return (
        (*FOLDERS, "materialization-raw", "grading"),
        ["preparation", "setup", "replay", "specification", "construction", "grading"]
        + (["native"] if profile == "current_native_preparation_failure" else []),
        grading_sources[profile],
    )


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_inventory(archive, *, snapshot=False):
    """Read original identities without manufacturing a missing per-file seal."""
    archive = Path(archive)
    assert not archive.is_symlink()
    extra = None
    if snapshot:
        folder = archive / "snapshot-restored"
        transport = archive / "snapshot-transport"
        assert not folder.is_symlink() and not transport.is_symlink()
        raw = (folder / "snapshot-files.json").read_bytes()
        transport_raw = (folder / "transport-export-manifest.json").read_bytes()
        assert (transport / "export-manifest.json").read_bytes() == transport_raw
        seal = json.loads(transport_raw)
        assert seal["download_checked"] is True
        rows = {row["path"]: row for row in seal["files"]}
        assert len(seal["files"]) == 2 and set(rows) == {"snapshot-files.json", "evidence.tar.gz"}
        assert rows["snapshot-files.json"]["bytes"] == len(raw)
        assert rows["snapshot-files.json"]["sha256"] == digest(raw)
        for name, row in rows.items():
            path = transport / name
            assert not path.is_symlink() and path.is_file()
            assert path.stat().st_size == row["bytes"]
            with path.open("rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]
        readback = json.loads((folder / "snapshot-readback.json").read_text())
        recovery_raw = (archive / "failure-archive-readback.json").read_bytes()
        recovery = json.loads(recovery_raw)
        assert recovery["snapshot"] == readback
        assert readback["format"] == "quiescent-tar-v1"
        assert readback["all_snapshot_files_hash_size_mode_verified"] is True
        assert readback["source_manifest_sha256"] == digest(raw)
        assert readback["transport_manifest_sha256"] == digest(transport_raw)
        manifest = json.loads(raw)
        assert manifest["source_quiescent"] is True
        assert readback["file_count"] == len(manifest["files"])
        assert readback["bytes"] == sum(row["bytes"] for row in manifest["files"])
        assert recovery["ordinary_autonomous_export_seal_reconstructed"] is False
        assert recovery["originals_changed"] is False
        extra = {
            "recovery_receipt_sha256": digest(recovery_raw),
            "transport_manifest_sha256": digest(transport_raw),
            "source_claim_sha256": recovery["source_claim_sha256"],
            "original_bootstrap_sha256": recovery["original_bootstrap_sha256"],
        }
    else:
        folder = archive
        raw = (folder / "sealed-manifest.json").read_bytes()
        manifest = json.loads(raw)
        readback = json.loads((folder / "independent-readback.json").read_text())
        assert readback["all_files_download_verified"] is True
        assert readback["source_manifest_sha256"] == digest(raw)
    rows = {row["path"]: row for row in manifest["files"]}
    assert len(rows) == len(manifest["files"])
    root = json.loads((archive / "root-evidence/readback.json").read_text())
    assert root["all_manifest_files_hash_size_mode_verified"] is True
    if snapshot:
        assert root["source_full_snapshot_manifest_sha256"] == digest(raw)
        assert root["root_manifest_sha256"] == digest(
            (archive / "root-evidence/sealed-root-manifest.json").read_bytes()
        )
    return folder / "files", rows, digest(raw), extra


def retained_hold(row, prior_hold, upper, *, refine=False):
    """Refine only closed, independently re-audited SDK lifetimes.

    The original full reservation remains mandatory for every new campaign.
    Refinement uses the existing research convention: add ten cents, then
    round upward to a quarter dollar, after the two 300-second clock margins.
    """
    if refine:
        assert row["state"] == "terminal_known_sdk_prefix_closed_lifetimes_reconciled"
        assert row["ceiling_usd"] == "1.00"
        assert Decimal(0) < upper < Decimal(1)
        retained = ((upper + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
            rounding=ROUND_CEILING
        ) * Decimal("0.25")
        assert Decimal(0) < retained < Decimal(1)
        return Decimal(1), retained
    assert row["ceiling_usd"] == f"{prior_hold:.2f}"
    return Decimal(prior_hold), Decimal(1)


def audit(pipeline, sources, claims, sessions, clean, *, profile="setup_replay"):
    folders, names, expected_sources = profile_config(profile)
    assert sources == expected_sources
    rejected = profile in {
        "current_setup_rejection",
        "legacy_specification_rejection",
        "current_specification_rejection",
        "current_grading_rejection",
        "common_grading_rejection",
    }
    assert pipeline["status"] == ("rejected" if rejected else "infrastructure_failed")
    if rejected:
        assert not pipeline.get("failed_stage")
    else:
        assert pipeline["failed_stage"] == names[-1]
    repair = pipeline.get("quality_repair")
    if profile == "current_comparison_repair_failure":
        assert repair and repair["kind"] == "comparison_diagnosis"
        assert repair["allowance_consumed"] is True and repair["target"] == "independent_solution"
        prefix = repair["original_materialization"].removesuffix("/materialization")
        assert repair["original_materialization"] == prefix + "/materialization"
        assert repair["original_grading"] == prefix + "/grading"
        assert set(repair) == {
            "kind",
            "allowance_consumed",
            "target",
            "original_materialization",
            "original_grading",
        }
    elif repair:
        # This exact controller's proposal revision/review uses direct model
        # calls, not another sandbox. Other repairs are not admitted here.
        assert profile in {
            "grading",
            "workspace_grading",
            "current_specification_rejection",
            "current_grading_rejection",
            "common_grading_rejection",
            "common_grading_failure",
            "current_grading_failure",
            "current_native_preparation_failure",
        }
        assert repair["kind"] == "specification_review"
        assert repair["target"] == "task_specification" and repair["allowance_consumed"] is True
        if profile == "current_specification_rejection":
            assert repair["validation_status"] in {"revise", "reject"}
            prefix = repair["original_specification"].removesuffix("/specification")
            assert repair["original_specification"] == prefix + "/specification"
            assert repair["original_review"] == prefix + "/specification-review"
            assert repair["effective_specification"] == prefix + "/specification-revision"
            assert repair["effective_review"] == prefix + "/specification-review-revised"
        else:
            assert repair["validation_status"] == "ready"
    stages = pipeline["stages"]
    assert [s["name"] for s in stages] == names
    assert [s["status"] for s in stages] == [
        *(["completed"] * (len(names) - 1)),
        "rejected" if rejected else "incomplete",
    ]
    assert pipeline["started"] <= stages[0]["started"]
    assert stages[-1]["finished"] <= pipeline["finished"]
    assert 0 < pipeline["finished"] - pipeline["started"] <= 7200
    assert all(s["started"] <= s["finished"] for s in stages)
    assert all(a["finished"] <= b["started"] for a, b in zip(stages, stages[1:], strict=False))
    assert set(claims) == set(sessions) == set(folders)
    assert len({c["id"] for c in claims.values()}) == len(folders)
    assert len({c["owner"] for c in claims.values()}) == len(folders)
    assert set(clean["owners"]) == {c["owner"] for c in claims.values()}
    assert clean["complete"] and clean["original_all_cleanup_passed"]
    assert clean["fresh_original_ids_absent"] and not clean["sandboxes"]
    for claim in claims.values():
        assert claim["state"] == "created"
        assert claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    stage_names = tuple(
        {
            "setup-raw": "setup",
            "replay": "replay",
            "materialization-raw": "construction",
            "grading": "grading",
            "grading-comparison-repair": "grading",
        }[folder]
        for folder in folders
    )
    for folder, name in zip(folders, stage_names, strict=True):
        stage = next(s for s in stages if s["name"] == name)
        assert stage["started"] <= sessions[folder]["started"]
        assert sessions[folder]["finished"] <= stage["finished"]
    assert all(
        sessions[a]["finished"] <= sessions[b]["started"]
        for a, b in zip(folders, folders[1:], strict=False)
    ), "The single-sandbox sessions must not overlap"
    coarse = len(folders) * RATE * 7500 / 3600
    assert coarse < len(folders)
    records = {
        folder: closed_session_bound(sessions[folder], pipeline, [], 300) for folder in folders
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
    p.add_argument(
        "--snapshot",
        action="store_true",
        help="Use the complete verified original quiescent snapshot, never a synthetic regular seal",
    )
    p.add_argument(
        "--refine-existing",
        action="store_true",
        help="Re-audit an already closed1USD hold; round its bound plus0.10USD upward to0.25USD",
    )
    p.add_argument(
        "--profile",
        choices=[
            "current_comparison_repair_failure",
            "current_setup_rejection",
            "setup_replay",
            "grading",
            "workspace_grading",
            "current_grading_rejection",
            "common_grading_rejection",
            "common_grading_failure",
            "current_grading_failure",
            "current_native_preparation_failure",
            "current_specification_rejection",
            "legacy_setup_replay",
            "legacy_specification_rejection",
        ],
        default="setup_replay",
    )
    a = p.parse_args()
    folders, _, expected_sources = profile_config(a.profile)
    assert not a.proof.exists()
    assert not a.snapshot or a.profile == "common_grading_failure"
    archive = a.private_root / f"archives/{a.number:03}"
    content_root, manifest, manifest_hash, snapshot_evidence = archive_inventory(
        archive, snapshot=a.snapshot
    )
    checked = {}

    def original(name):
        path = content_root / name
        assert not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == manifest[name]["bytes"]
        assert digest(data) == manifest[name]["sha256"]
        checked[name] = digest(data)
        return json.loads(data)

    launch = a.private_root / "launch"
    claim_raw = (launch / f"{a.number:03}-submission.json").read_bytes()
    submission = json.loads(claim_raw)
    if snapshot_evidence:
        assert snapshot_evidence["source_claim_sha256"] == digest(claim_raw)
        assert (
            snapshot_evidence["original_bootstrap_sha256"]
            == submission["inputs"]["files"]["bootstrap.py"]
        )
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
            for name in expected_sources
        }
    common_admission = None
    if a.profile in {"common_grading_rejection", "common_grading_failure"}:
        runtime, common_admission = common_runtime()
        with tarfile.open(payload / "biotasks.tar") as packet:
            check_common_payload(packet, config, runtime)
    clean_raw = (archive / "fresh-provider-cleanup.json").read_bytes()
    clean = json.loads(clean_raw)
    assert (
        clean["source_snapshot_manifest_sha256" if a.snapshot else "source_archive_manifest_sha256"]
        == manifest_hash
    )
    if a.snapshot:
        assert clean["source_archive_format"] == "quiescent-tar-v1"
        assert (
            clean["source_transport_manifest_sha256"]
            == snapshot_evidence["transport_manifest_sha256"]
        )
    assert clean["source_configuration_sha256"] == digest(
        (payload / "campaign-config.json").read_bytes()
    )
    assert {n for n in manifest if n.endswith("/sandbox-claim.json")} == {
        f + "/sandbox-claim.json" for f in folders
    }
    forbidden = () if a.profile == "current_native_preparation_failure" else ("native/",)
    if a.profile == "current_setup_rejection":
        forbidden += ("replay/",)
    if a.profile not in {
        "current_comparison_repair_failure",
        "grading",
        "workspace_grading",
        "current_grading_rejection",
        "common_grading_rejection",
        "common_grading_failure",
        "current_grading_failure",
        "current_native_preparation_failure",
    }:
        forbidden += ("materialization", "grading")
        if a.profile not in {"legacy_specification_rejection", "current_specification_rejection"}:
            forbidden += ("specification/",)
    assert not any(n.startswith(forbidden) for n in manifest)
    assert {r["path"] for r in clean["original_cleanup_evidence"]} == {
        f + "/cleanup.json" for f in folders
    }
    claims, sessions = {}, {}
    for folder in folders:
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
    coarse, upper, records = audit(pipeline, sources, claims, sessions, clean, profile=a.profile)
    native_preparation = None
    if a.profile == "current_native_preparation_failure":
        # A native failure alone is insufficient: prove the exact frozen runner
        # never dispatched a supervisor, then price every preceding SDK session.
        native_sources = frozen_sources(payload, submission["inputs"]["files"])
        native_claims = [
            original(name) for name in sorted(manifest) if name.startswith("native/trial-claims/")
        ]
        native_preparation = audit_no_dispatch(
            pipeline,
            original("native/result.json"),
            original("native/oracle/trial.json"),
            native_claims,
            list(manifest),
            native_sources,
        )
    observations = [
        json.loads(p.read_text())
        for p in (launch / "typed-observations").glob(f"{a.number:03}-*.json")
    ]
    terminal = max(observations, key=lambda r: r["observed_at"])
    assert terminal["terminal"] and terminal["state"] == (
        "SUCCEEDED"
        if a.profile
        in {
            "current_setup_rejection",
            "legacy_specification_rejection",
            "current_specification_rejection",
            "current_grading_rejection",
            "common_grading_rejection",
        }
        else "FAILED"
    )
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
    native_unused = a.profile == "current_native_preparation_failure"
    whole_grading_failure = a.profile == "common_grading_failure"
    prior_hold = len(folders) + int(native_unused or whole_grading_failure)
    previous, retained = retained_hold(row, prior_hold, upper, refine=a.refine_existing)
    if not a.refine_existing:
        if a.profile == "current_comparison_repair_failure" or whole_grading_failure:
            assert previous == 5 and row["state"] == "submitted"
        else:
            assert row["state"] == (
                "terminal_native_preparation_failure_full_reservation_held"
                if native_unused
                else "unused_stage_allowances_released_used_holds_unchanged"
            )
    row.update(
        ceiling_usd=f"{retained:.2f}",
        state="terminal_known_sdk_prefix_closed_lifetimes_refined"
        if a.refine_existing
        else "terminal_known_sdk_prefix_closed_lifetimes_reconciled",
        reconciliation="All complete original SDK sessions priced at full resources plus300seconds at EACH end, against exact reviewed source family and fresh cleanup. "
        + ("Add0.10USD and round upward to0.25USD; " if a.refine_existing else "Retain1USD; ")
        + "no invoices or credits assumed. See "
        + a.proof.relative_to(a.ledger.parent).as_posix(),
    )
    released = previous - retained
    ledger.update(
        reserved_upper_bound_usd=f"{held - released:.2f}",
        unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held + released:.2f}",
    )
    after = (json.dumps(ledger, indent=2) + "\n").encode()
    proof = dict(
        observed_at=datetime.now(UTC).isoformat(),
        campaign=a.number,
        profile=a.profile,
        applied=a.apply,
        helper_sha256=digest(Path(__file__).read_bytes()),
        clock_helper_sha256=digest(
            Path(__file__).resolve().parents[1].joinpath("070/closed_session_bound.py").read_bytes()
        ),
        source_manifest_sha256=manifest_hash,
        original_archive_format="quiescent-tar-v1" if a.snapshot else "per-file-export-v1",
        original_snapshot_evidence=snapshot_evidence,
        source_ledger_sha256=digest(before),
        result_ledger_sha256=digest(after),
        checked_originals=checked,
        frozen_implementation_sha256=sources,
        fresh_cleanup_sha256=digest(clean_raw),
        terminal=terminal,
        coarse_full_lifetimes_bound_usd=str(coarse),
        resource_upper_bound_usd=str(upper),
        records=records,
        native_preparation_non_dispatch=native_preparation,
        common_source_admission=common_admission,
        retained_usd=f"{retained:.2f}",
        previous_hold_usd=f"{previous:.2f}",
        refinement=a.refine_existing,
        additional_margin_usd="0.10" if a.refine_existing else None,
        rounding="upward_to_0.25USD" if a.refine_existing else None,
        released_usd=f"{released:.2f}",
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
