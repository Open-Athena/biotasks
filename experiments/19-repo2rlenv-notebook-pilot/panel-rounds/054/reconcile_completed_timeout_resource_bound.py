"""Audit complete serial runs, including handled solver timeouts, for resource cost.

This is post-run exposure accounting, not a provider invoice or a change to the
original execution ceilings. No model, scientific or provider calls occur here.
"""

import argparse
import ast
import hashlib
import json
import tarfile
import tomllib
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from native_resource_record import verify_native_resource_record

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("numbers", type=int, nargs="+")
parser.add_argument("--private-root", type=Path, required=True)
parser.add_argument("--harbor-wheel", type=Path, required=True)
parser.add_argument("--ledger", type=Path, required=True)
parser.add_argument("--proof", type=Path, required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
assert len(set(args.numbers)) == len(args.numbers) and not args.proof.exists()
ledger_before = args.ledger.read_bytes()
ledger = json.loads(ledger_before)
assert sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"]) == Decimal(
    ledger["reserved_upper_bound_usd"]
)
records = []
for number in args.numbers:
    archive = args.private_root / f"archives/{number:03}"
    raw_manifest = (archive / "sealed-manifest.json").read_bytes()
    manifest = {r["path"]: r for r in json.loads(raw_manifest)["files"]}
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == hashlib.sha256(raw_manifest).hexdigest()
    root_readback = json.loads((archive / "root-evidence/readback.json").read_text())
    assert root_readback["all_manifest_files_hash_size_mode_verified"]
    checked = {}

    def original(name, archive=archive, manifest=manifest, checked=checked):
        raw = (archive / "files" / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest[name]["sha256"]
        assert len(raw) == manifest[name]["bytes"]
        checked[name] = manifest[name]["sha256"]
        return json.loads(raw)

    pipeline = original("pipeline.json")
    assert pipeline["status"] == "validated"
    assert [r["name"] for r in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
        "native",
    ]
    assert all(r["status"] == "completed" for r in pipeline["stages"])
    assert pipeline["finished"] - pipeline["started"] <= 7200
    for left, right in zip(pipeline["stages"], pipeline["stages"][1:], strict=False):
        assert left["finished"] <= right["started"]
    payload = args.private_root / f"launch/{number:03}-payload"
    claim = json.loads((args.private_root / f"launch/{number:03}-submission.json").read_text())
    raw_config = (payload / "campaign-config.json").read_bytes()
    assert (
        hashlib.sha256(raw_config).hexdigest() == claim["inputs"]["files"]["campaign-config.json"]
    )
    config = json.loads(raw_config)
    assert config["campaign_seconds"] == 7200 and config["cleanup_seconds"] == 300
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }
    clean = json.loads((archive / "fresh-provider-cleanup.json").read_text())
    assert clean["complete"] and clean["original_all_cleanup_passed"]
    assert clean["fresh_original_ids_absent"] and not clean["sandboxes"]
    assert clean["source_archive_manifest_sha256"] == readback["source_manifest_sha256"]
    assert clean["source_configuration_sha256"] == hashlib.sha256(raw_config).hexdigest()
    expected_cleanup = {
        "setup-raw/cleanup.json",
        "replay/cleanup.json",
        "materialization-raw/cleanup.json",
        "grading/cleanup.json",
        "native/oracle/remote-job.json",
        "native/nop/remote-job.json",
        "native/terminus-2/remote-job.json",
    }
    assert {r["path"] for r in clean["original_cleanup_evidence"]} == expected_cleanup
    assert len(clean["owners"]) == len(expected_cleanup) == 7
    for row in clean["original_cleanup_evidence"]:
        assert (
            original(row["path"])["cleanup"]["passed"]
            if row["path"].startswith("native/")
            else original(row["path"])["passed"]
        )
    for stage in ["setup-raw", "replay", "materialization-raw", "grading"]:
        observed = original(stage + "/sandbox-claim.json")
        assert observed["state"] == "created"
        assert observed["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
    upstream = payload / "upstream.tar.gz"
    with upstream.open("rb") as stream:
        assert (
            hashlib.file_digest(stream, "sha256").hexdigest()
            == claim["inputs"]["files"]["upstream.tar.gz"]
        )
    with tarfile.open(upstream) as source:
        lock_names = [n.name for n in source if n.name.endswith("/uv.lock")]
        assert len(lock_names) == 1
        lock = tomllib.loads(source.extractfile(lock_names[0]).read().decode())
    harbor = next(p for p in lock["package"] if p["name"] == "harbor")
    assert harbor["version"] == "0.22.0" and len(harbor["wheels"]) == 1
    with args.harbor_wheel.open("rb") as stream:
        wheel_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    assert "sha256:" + wheel_hash == harbor["wheels"][0]["hash"]
    with zipfile.ZipFile(args.harbor_wheel) as wheel:
        backend = wheel.read("harbor/environments/daytona/environment.py")
    constructors = [
        n
        for n in ast.walk(ast.parse(backend))
        if isinstance(n, ast.FunctionDef)
        and n.name == "__init__"
        and any(a.arg == "auto_snapshot" for a in [*n.args.args, *n.args.kwonlyargs])
    ]
    assert len(constructors) == 1
    signature = constructors[0].args
    defaults = dict(
        zip(
            [a.arg for a in signature.args][len(signature.args) - len(signature.defaults) :],
            signature.defaults,
            strict=True,
        )
    )
    defaults.update(zip([a.arg for a in signature.kwonlyargs], signature.kw_defaults, strict=True))
    assert (
        isinstance(defaults["auto_snapshot"], ast.Constant)
        and defaults["auto_snapshot"].value is False
    )
    assert (
        isinstance(defaults["snapshot_template_name"], ast.Constant)
        and defaults["snapshot_template_name"].value is None
    )
    native_intervals = []
    native_exceptions = {}
    for agent in ["oracle", "nop", "terminus-2"]:
        prefix = f"native/{agent}"
        metadata = original(prefix + "/trial.json")
        result_names = [
            name
            for name, row in manifest.items()
            if name.startswith(prefix + "/")
            and name.endswith("/result.json")
            and row["sha256"] == metadata["result_sha256"]
        ]
        assert len(result_names) == 1
        native_exceptions[agent] = verify_native_resource_record(
            agent, metadata, original(result_names[0])
        )
        assert metadata["resource_overrides"] == {"cpus": 4, "memory_mb": 8192, "storage_mb": 10240}
        job_name = config["campaign"] + "-native-" + agent
        native_config = original(prefix + "/" + job_name + "/config.json")
        assert native_config["n_concurrent_trials"] == 1 and len(native_config["tasks"]) == 1
        environment = native_config["environment"]
        assert environment["type"] == "daytona"
        assert {
            k: environment[k]
            for k in ["override_cpus", "override_memory_mb", "override_storage_mb"]
        } == {"override_cpus": 4, "override_memory_mb": 8192, "override_storage_mb": 10240}
        assert set(environment["kwargs"]) <= {"labels", "auto_stop_interval_mins"}
        native_intervals.append(
            tuple(
                datetime.fromisoformat(metadata[k]).timestamp()
                for k in ["started_at", "finished_at"]
            )
        )
    assert all(a[1] <= b[0] for a, b in zip(native_intervals, native_intervals[1:], strict=False))
    native_stage = pipeline["stages"][-1]
    assert (
        native_stage["started"]
        <= native_intervals[0][0]
        <= native_intervals[-1][1]
        <= native_stage["finished"]
    )
    row = next(
        r for r in ledger["reservations"] if r["scope"].startswith(f"autonomous-panel-{number:03}:")
    )
    assert row["ceiling_usd"] == "5.00"
    # Price twice the verified serial sandbox exposure, over the full approved
    # lifetime rather than the shorter observed duration. Retain further margin.
    rate = 4 * Decimal("0.0504") + 8 * Decimal("0.0162") + 10 * Decimal("0.000108")
    bound = 2 * rate * Decimal(7500) / Decimal(3600)
    assert bound == Decimal("1.384500") < Decimal("2.00")
    records.append(
        {
            "campaign": number,
            "source_manifest_sha256": readback["source_manifest_sha256"],
            "checked_originals": checked,
            "actual_serial_pipeline_seconds": str(pipeline["finished"] - pipeline["started"]),
            "native_intervals": native_intervals,
            "native_exception_types": native_exceptions,
            "exceptions_do_not_change_scientific_outcomes": True,
            "original_and_fresh_seven_owner_cleanup_verified": True,
            "locked_harbor_wheel_sha256": wheel_hash,
            "locked_daytona_backend_sha256": hashlib.sha256(backend).hexdigest(),
            "native_auto_snapshot_default": False,
            "native_snapshot_overrides": False,
            "profile_hourly_usd": str(rate),
            "conservatively_priced_parallel_sandboxes": 2,
            "full_approved_lifetime_seconds": 7500,
            "resource_charge_upper_bound_usd": str(bound),
            "retained_usd": "2.00",
            "additional_margin_usd": str(Decimal(2) - bound),
            "released_excess_escrow_usd": "3.00",
        }
    )
    row.update(
        ceiling_usd="2.00",
        state="terminal_full_lifecycle_resource_bound_reconciled",
        reconciliation="Verified completed serial stages and native trials, full original archive/root readback, original/fresh seven-owner absence, pinned no-snapshot backend and exact resource overrides. Retain2USDagainst1.384500USDtwice-serial full-lifetime resource bound, no credits or invoice assumption. See "
        + args.proof.relative_to(args.ledger.parent).as_posix(),
    )
held = sum(Decimal(r["ceiling_usd"]) for r in ledger["reservations"])
ledger.update(
    reserved_upper_bound_usd=f"{held:.2f}",
    unallocated_usd=f"{Decimal(ledger['ceiling_before_credits']) - held:.2f}",
)
after = (json.dumps(ledger, indent=2) + "\n").encode()
proof = {
    "observed_at": datetime.now(UTC).isoformat(),
    "applied": args.apply,
    "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_ledger_sha256": hashlib.sha256(ledger_before).hexdigest(),
    "result_ledger_sha256": hashlib.sha256(after).hexdigest(),
    "rates_source": "https://www.daytona.io/pricing",
    "billing_source": "https://www.daytona.io/docs/billing",
    "rates_verified_date": "2026-10-25",
    "records": records,
    "aggregate_authorized_usd": ledger["ceiling_before_credits"],
    "aggregate_held_after_usd": ledger["reserved_upper_bound_usd"],
    "unallocated_after_usd": ledger["unallocated_usd"],
    "actual_invoice_usd": None,
    "free_credits_assumed": False,
    "original_limits_or_scientific_outcomes_changed": False,
    "base_strict_auditor_sha256": "036241de95a1d148af94020839568966c80bb14bba7202c36d73cbc4324cb772",
    "native_resource_record_validator_sha256": hashlib.sha256(
        Path(__file__).with_name("native_resource_record.py").read_bytes()
    ).hexdigest(),
    "profile_difference": "Allow only a handled600secondsolverAgentTimeoutError with originalresultverification, completedwrapper, returncode0 and retries0; all original resource/interval/archive/cleanup/backend constraints retained.",
    "new_resources_or_models": 0,
}
args.proof.parent.mkdir(parents=True, exist_ok=True)
args.proof.write_text(json.dumps(proof, indent=2) + "\n")
if args.apply:
    assert args.ledger.read_bytes() == ledger_before
    args.ledger.write_bytes(after)
print(json.dumps({k: v for k, v in proof.items() if k != "records"}))
