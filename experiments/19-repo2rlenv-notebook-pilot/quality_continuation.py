"""Import hash-bound native evidence into upstream's existing quality entrypoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.quality.loop.artifacts import import_trial
from repo2rlenv.quality.loop.models import ProbeManifest


def load(directory: Path) -> tuple[Path, dict[str, Path], dict]:
    plan = json.loads((directory / "continuation.json").read_text())
    for name, expected in plan["files"].items():
        path = directory / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink():
            raise ValueError("Unsafe continuation input")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            raise ValueError("Continuation evidence changed")
        if path.stat().st_mode & 0o777 != expected["mode"]:
            raise ValueError("Continuation evidence modes changed")
    task = directory / plan["task"]
    identity = inspect_bundle(task)
    if not identity["integrity_passed"] or identity["bundle_hash"] != plan["bundle_hash"]:
        raise ValueError("Continuation task identity changed")
    evidence = {
        role: directory / plan["evidence"][role] for role in ("baseline", "oracle", "rollout")
    }
    for role, path in evidence.items():
        if path.relative_to(directory).as_posix() not in plan["files"]:
            raise ValueError("Unbound native evidence")
        imported = import_trial(path, task, role)
        if imported.exception_type is not None or imported.reward is None:
            raise ValueError("Cannot import an incomplete native trial")
    for name in (plan["probes"], plan["cleanup_reconciliation"]):
        if name not in plan["files"]:
            raise ValueError("Unbound continuation metadata")
    probes = directory / plan["probes"]
    known = ProbeManifest.model_validate_json(probes.read_text())
    if known.bundle_hash != identity["bundle_hash"]:
        raise ValueError("Known probes belong to a different task")
    evidence["probes"] = probes
    cleanup = json.loads((directory / plan["cleanup_reconciliation"]).read_text())
    if not cleanup["complete"] or cleanup["sandboxes"] or cleanup["exact_id_state"] != "absent":
        raise ValueError("Original execution cleanup remains unresolved")
    return task, evidence, plan


def remaining_config(config: dict, plan: dict) -> dict:
    """Carry prior consumption forward; a replacement never resets attempt budgets."""
    updated = json.loads(json.dumps(config))
    for scope, consumed in plan["prior_requests"].items():
        if consumed < 0:
            raise ValueError("Invalid prior request count")
        updated["request_allowances"][scope]["requests"] -= consumed
    if any(v["requests"] < 1 for v in updated["request_allowances"].values()):
        raise ValueError("Required continuation request allowance is exhausted")
    for name, consumed in (
        ("max_trials", plan["prior_trials"]),
        ("max_solver_attempts", plan["prior_solver_attempts"]),
        ("max_quality_repairs", plan["prior_quality_repairs"]),
    ):
        if consumed < 0:
            raise ValueError("Invalid prior execution count")
        updated[name] -= consumed
    if updated["max_trials"] < 1 or updated["max_solver_attempts"] != 1:
        raise ValueError("Continuation requires remaining trials and exactly one solver slot")
    if updated["max_quality_repairs"] < 0:
        raise ValueError("Quality repair allowance exhausted")
    return updated
