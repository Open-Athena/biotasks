"""Release only undispatched stages in the archived five-stage reservation profile.

This does not measure invoices, assume credits or reduce any dispatched-stage
allowance. Provider cleanup and typed terminal observations must already exist.
"""

import argparse
import ast
import hashlib
import json
import tarfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("numbers", type=int, nargs="+")
parser.add_argument("--private-root", type=Path, required=True)
parser.add_argument("--ledger", type=Path, required=True)
parser.add_argument("--proof", type=Path, required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
assert len(set(args.numbers)) == len(args.numbers) and not args.proof.exists()
proof_reference = (
    args.proof.relative_to(args.ledger.parent).as_posix()
    if args.proof.is_relative_to(args.ledger.parent)
    else args.proof.name
)
before = args.ledger.read_bytes()
ledger = json.loads(before)
ceiling = Decimal(ledger["ceiling_before_credits"])
held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
assert held == Decimal(ledger["reserved_upper_bound_usd"]) <= ceiling
records = []
for number in args.numbers:
    launch = args.private_root / "launch"
    archive = args.private_root / f"archives/{number}"
    claim_raw = (launch / f"{number:03}-submission.json").read_bytes()
    claim = json.loads(claim_raw)
    observations = [
        json.loads(p.read_text())
        for p in (launch / "typed-observations").glob(f"{number:03}-*.json")
    ]
    terminal = max(observations, key=lambda row: row["observed_at"])
    assert terminal["state"] == "SUCCEEDED" and terminal["terminal"]
    assert terminal["claim_sha256"] == hashlib.sha256(claim_raw).hexdigest()
    manifest_raw = (archive / "sealed-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest()
    root = json.loads((archive / "root-evidence/readback.json").read_text())
    assert root["all_manifest_files_hash_size_mode_verified"]
    raw = (archive / "files/pipeline.json").read_bytes()
    original = next(row for row in manifest["files"] if row["path"] == "pipeline.json")
    assert len(raw) == original["bytes"]
    assert hashlib.sha256(raw).hexdigest() == original["sha256"]
    pipeline = json.loads(raw)
    assert pipeline["status"] == "rejected"
    assert all(row["status"] in {"completed", "rejected"} for row in pipeline["stages"])
    payload = launch / f"{number:03}-payload"
    config_raw = (payload / "campaign-config.json").read_bytes()
    assert (
        hashlib.sha256(config_raw).hexdigest() == claim["inputs"]["files"]["campaign-config.json"]
    )
    config = json.loads(config_raw)
    assert Decimal(config["daytona_budget_usd"]) == 5
    packet = payload / "biotasks.tar"
    with packet.open("rb") as stream:
        assert (
            hashlib.file_digest(stream, "sha256").hexdigest()
            == claim["inputs"]["files"]["biotasks.tar"]
        )
    with tarfile.open(packet) as source:
        controller = source.extractfile(
            "experiments/19-repo2rlenv-notebook-pilot/run_autonomous.py"
        ).read()
    cls = next(
        n
        for n in ast.parse(controller).body
        if isinstance(n, ast.ClassDef) and n.name == "Pipeline"
    )
    step = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "step")
    increment = next(
        n.value
        for n in ast.walk(step)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "reservation" for t in n.targets)
    )
    assert isinstance(increment, ast.BinOp) and isinstance(increment.op, ast.Add)
    assert ast.unparse(increment.left) == "self.receipt['daytona_reserved_usd']"
    reservation_definition_sha256 = None
    if isinstance(increment.right, ast.Constant):
        assert type(increment.right.value) is int and increment.right.value == 1
    else:
        assert ast.unparse(increment.right) == "float(STAGE_RESERVATION_USD)"
        with tarfile.open(packet) as source:
            definition = source.extractfile(
                "experiments/19-repo2rlenv-notebook-pilot/campaign_budget.py"
            ).read()
        declared = [
            node.value
            for node in ast.parse(definition).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "STAGE_RESERVATION_USD"
                for target in node.targets
            )
        ]
        assert len(declared) == 1
        value = declared[0]
        assert isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
        assert value.func.id == "Decimal" and len(value.args) == 1 and not value.keywords
        assert isinstance(value.args[0], ast.Constant) and type(value.args[0].value) is str
        assert Decimal(value.args[0].value) == Decimal("1.00")
        reservation_definition_sha256 = hashlib.sha256(definition).hexdigest()
    calls = sorted(
        [
            n
            for n in ast.walk(cls)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "self"
            and n.func.attr == "step"
            and any(
                k.arg == "paid" and isinstance(k.value, ast.Constant) and k.value.value is True
                for k in n.keywords
            )
        ],
        key=lambda n: n.lineno,
    )
    stages = [ast.literal_eval(n.args[0]) for n in calls]
    assert stages == ["setup", "replay", "construction", "grading", "native"]
    used = [row["name"] for row in pipeline["stages"] if row["name"] in stages]
    assert used == stages[: len(used)] and len(used) < len(stages)
    reserved = Decimal(str(pipeline["daytona_reserved_usd"]))
    assert reserved == len(used)
    cleanup = json.loads((archive / "fresh-provider-cleanup.json").read_text())
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["fresh_original_ids_absent"] and not cleanup["sandboxes"]
    assert cleanup["source_archive_manifest_sha256"] == readback["source_manifest_sha256"]
    assert cleanup["source_configuration_sha256"] == hashlib.sha256(config_raw).hexdigest()
    assert len(cleanup["original_cleanup_evidence"]) == len(used)
    row = next(
        r for r in ledger["reservations"] if r["scope"].startswith(f"autonomous-panel-{number:03}:")
    )
    assert Decimal(row["ceiling_usd"]) == 5
    release = Decimal(5) - reserved
    records.append(
        {
            "campaign": number,
            "controller_sha256": hashlib.sha256(controller).hexdigest(),
            "reservation_expression": ast.unparse(increment.right),
            "reservation_definition_sha256": reservation_definition_sha256,
            "source_archive_manifest_sha256": readback["source_manifest_sha256"],
            "terminal": terminal,
            "cleanup_observed_at": cleanup["observed_at"],
            "dispatched_stages": used,
            "undispatched_stages": stages[len(used) :],
            "prior_hold_usd": "5.00",
            "retained_full_dispatched_stage_hold_usd": f"{reserved:.2f}",
            "released_unused_stage_allowance_usd": f"{release:.2f}",
        }
    )
    row.update(
        ceiling_usd=f"{reserved:.2f}",
        state="unused_stage_allowances_released_used_holds_unchanged",
        reconciliation="Retain1USDfor every original dispatched sandbox stage; release only mandatory stages never dispatched. Full original archives, exact frozen reservation code, typed terminal state and fresh original-ID/owner cleanup verified. Not an invoice, credits or used-provider cost audit. See "
        + proof_reference
        + ".",
    )
released = sum(Decimal(row["released_unused_stage_allowance_usd"]) for row in records)
after_held = sum(Decimal(row["ceiling_usd"]) for row in ledger["reservations"])
assert after_held == held - released and after_held <= ceiling
ledger.update(
    reserved_upper_bound_usd=f"{after_held:.2f}", unallocated_usd=f"{ceiling - after_held:.2f}"
)
after = (json.dumps(ledger, indent=2) + "\n").encode()
proof = {
    "observed_at": datetime.now(UTC).isoformat(),
    "reconciliation_helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "applied": args.apply,
    "source_ledger_sha256": hashlib.sha256(before).hexdigest(),
    "result_ledger_sha256": hashlib.sha256(after).hexdigest(),
    "records": records,
    "released_unused_allowance_usd": f"{released:.2f}",
    "aggregate_authorized_usd": f"{ceiling:.2f}",
    "aggregate_held_after_usd": f"{after_held:.2f}",
    "unallocated_after_usd": f"{ceiling - after_held:.2f}",
    "no_used_provider_holds_reclaimed": True,
    "new_resources_or_model_calls": 0,
    "scope": "Reservation bookkeeping only; no actual invoice, price, credit or refund claim.",
}
args.proof.parent.mkdir(parents=True, exist_ok=True)
args.proof.write_text(json.dumps(proof, indent=2) + "\n")
if args.apply:
    assert args.ledger.read_bytes() == before
    args.ledger.write_bytes(after)
    assert args.ledger.read_bytes() == after
print(json.dumps({k: v for k, v in proof.items() if k != "records"}))
