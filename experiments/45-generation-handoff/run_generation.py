"""Plan or resume one bounded official generation, preserving the full lifecycle."""

import argparse
import copy
import importlib.util
import json
import re
import shutil
import time
import urllib.request
from pathlib import Path

from biotasks.validation import bridge
from biotasks.validation.archives import pack
from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json
from biotasks.validation.planning import TOOLS, UPSTREAM, code_files, code_identity
from generation_pipeline import GenerationPipeline

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[3]
OWN_CODE = [
    "run_generation.py",
    "generation_entry.py",
    "generation_worker.py",
    "generation_client.py",
    "generation_bridge.py",
    "generation_pipeline.py",
    "generation_publication.py",
    "model_budget.py",
]


def verify(root):
    plan = read_json(root / "plan.json")
    original = copy.deepcopy(plan)
    identity = original.pop("plan_identity")
    require(json_sha(original) == identity, "Generation plan changed")
    require(plan["validation_code_identity"] == code_identity(), "Shared lifecycle code changed")
    require(
        sha(Path(plan["backend"]["config"])) == plan["backend_config_sha256"],
        "SDK configuration changed",
    )
    for name, digest in plan["own_code_sha256"].items():
        require(sha(ROOT / name) == digest, "Generation adapter code changed")
    group = plan["group"]
    for name, digest in group["payload_sha256"].items():
        require(sha(root / group["payload_directory"] / name) == digest, "Frozen payload changed")
    require(
        sha(root / group["notices"]["path"]) == group["notices"]["sha256"], "Source notices changed"
    )
    return plan


def prepare(root, backend, ledger, run_id, profile=None):
    require(not root.exists(), "Never overwrite a generation plan")
    require(re.fullmatch(r"[a-z][a-z0-9-]{0,95}", run_id), "Invalid fixed run identity")
    root.mkdir(parents=True, mode=0o700)
    old = BASE / "experiments/28-catalogued-fields"
    source = BASE / ".research-worktrees/31/experiments/31-historical-builds"
    native = read_json(ROOT / "proposed-native-config.json")
    frozen_candidates = read_json(ROOT / "reference-candidates.json")
    require(
        native["repo"]["url"] == "https://github.com/" + frozen_candidates["repo"]
        and len(frozen_candidates["candidates"]) == 1,
        "Reference scope changed",
    )
    policy_source = old / "history-wide/cost_guard.py"
    spec = importlib.util.spec_from_file_location("reference_cost_guard", policy_source)
    pricing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pricing)
    with urllib.request.urlopen(pricing.URL, timeout=30) as response:
        raw = response.read(1024**2 + 1)
    require(len(raw) <= 1024**2, "Pricing quote exceeds bound")
    quote = json.loads(raw)
    maximum = str(pricing.reservation(quote, 2048) + __import__("decimal").Decimal(5))
    write_json(root / "price-quote.json", quote)
    model = {
        "maximum_usd": maximum,
        "quote_sha256": sha(root / "price-quote.json"),
        "actual_stop_usd": "5",
        "only_original_upstream_calls": True,
    }
    resources = {
        "cpus": 4,
        "memory_gib": 16,
        "disk_gib": 30,
        "timeout_seconds": 5400,
        "work_deadline_seconds": 5000,
        "maximum_cpu_hours": 6,
        "cleanup_cpu_hours": 1 / 6,
    }
    payload = root / "payload"
    payload.mkdir()
    base = read_json(old / "input-checkpoint.json")
    reused = {}
    for name in (
        "native_docker.py",
        "setup_controller.sh",
        "observed_cli.py",
        "provider_usage.py",
        "pins.json",
    ):
        path = old / name
        require(
            sha(path) == base["payload_files"][name]["sha256"],
            "Baseline infrastructure asset changed",
        )
        shutil.copyfile(path, payload / name)
        reused[name] = sha(path)
    shutil.copyfile(policy_source, payload / "cost_guard.py")
    for name in ("generation_entry.py", "generation_worker.py"):
        shutil.copyfile(ROOT / name, payload / name)
    for name, data in code_files().items():
        path = payload / "biotasks/validation" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (payload / "biotasks/__init__.py").write_text("")
    shutil.copyfile(source / "package-acquisition.json", payload / "upstream-source-manifest.json")
    shutil.copyfile(ROOT / "reference-candidates.json", payload / "reference-candidates.json")
    write_json(payload / "native-config.json", native)
    write_json(payload / "model-run-budget.json", model)
    write_json(
        payload / "family.json",
        {
            "run_id": run_id,
            "operation": "generate",
            "network": backend["network"],
            "tools": TOOLS,
            "resources": resources,
            "model_budget": model,
        },
    )
    write_json(
        payload / "payload.json",
        {
            "run_id": run_id,
            "sha256": {
                p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
            },
        },
    )
    shutil.copyfile(payload / "native-config.json", root / "native-config.json")
    shutil.copyfile(ROOT / "reference-candidates.json", root / "reference-candidates.json")
    notices = (
        BASE
        / ".research-worktrees/44/experiments/44-validation-entrypoint/inputs-private/opencobra__cobrapy/notices"
    )
    require(bool(inventory(notices)), "Missing previously reviewed source notices")
    package = pack(notices, root / "notices.tar.gz")
    package["path"] = "notices.tar.gz"
    policy = {
        "eligible": True,
        "review": "Pinned publicly eligible Cobrapy source/ref and PR1497 notices, original official bootstrap/generation with only original observed model calls. Exact bounded text task/cache/observation/native logs and own source metadata only; no images, environments, whole-account billing, credentials, biological datasets or Matchms. JSON-gzip observation bytes undergo bounded decoded JSON/text/credential inspection before publication.",
    }
    group = {
        "id": "generation",
        "run_id": run_id,
        "resources": resources,
        "payload_directory": "payload",
        "payload_sha256": {
            p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
        },
        "notices": package,
        "publication": policy,
    }
    if profile is None:
        profile = bridge.call(backend, {"action": "fingerprint"}, root / "client-profile.log")
    plan = {
        "schema_version": 1,
        "kind": "official generation lifecycle, not native validation",
        "repo2rlenv_revision": UPSTREAM,
        "backend": backend,
        "backend_config_sha256": sha(Path(backend["config"])),
        "client_profile": profile,
        "budget_ledger": str(ledger),
        "archive": {
            "kind": "hf-public",
            "bucket": "open-athena/biotasks",
            "prefix": "research/45-generation-handoff",
        },
        "validation_code_identity": code_identity(),
        "own_code_sha256": {name: sha(ROOT / name) for name in OWN_CODE},
        "model_budget": model,
        "reused_baseline_sha256": reused,
        "original_cost_guard_sha256": sha(policy_source),
        "group": group,
        "new_capacity_allowed": False,
        "task_repairs": False,
        "admission_state": "not admitted; no remote or model calls in preparation",
    }
    plan["plan_identity"] = json_sha(plan)
    write_json(root / "plan.json", plan)
    return verify(root)


def run(root, once=False):
    plan = verify(root)
    pipeline = GenerationPipeline(root, plan, plan["group"])
    while True:
        state = pipeline.step()
        if state == "complete":
            readback = read_json(pipeline.directory / "readback.json")
            held = (
                (pipeline.directory / "model-budget-hold.json").exists()
                or (pipeline.directory / "budget-hold.json").exists()
                or not readback["model_billing"]["complete"]
            )
            return {
                "state": "held" if held else "complete",
                "generation_workflow": state,
                "exported_tasks": readback["exported_tasks"],
                "model_billing": readback["model_billing"],
                "native_controls_run": False,
                "next": "Audited local handoff and ordinary validator CLI; do not regenerate",
            }
        if state.startswith("held:") or once:
            return {"state": state, "run_id": plan["group"]["run_id"]}
        stage = state.split(":", 1)[-1]
        if (
            stage
            in {
                "submission_recorded",
                "remote_terminal",
                "archive_readback_verified",
                "cleanup_terminal",
            }
            and not (pipeline.directory / (stage + ".json")).exists()
        ):
            time.sleep(300)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["plan", "run", "status"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--run-id",
        help="Required new fixed identity for planning; never replaces an existing handle",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "plan":
        require(bool(args.run_id), "Planning needs an explicit new fixed run identity")
        backend = read_json(
            BASE
            / ".research-worktrees/44/experiments/44-validation-entrypoint/native-manifest.json"
        )["backend"]
        ledger = BASE / ".research-worktrees/33/experiments/33-unattended-validation/budget.json"
        result = prepare(root, backend, ledger, args.run_id)
        print(
            json.dumps(
                {
                    "plan_identity": result["plan_identity"],
                    "run_id": result["group"]["run_id"],
                    "maximum_model_usd": result["model_budget"]["maximum_usd"],
                    "admitted": False,
                }
            )
        )
    elif args.action == "run":
        print(json.dumps(run(root, args.once), indent=2))
    else:
        plan = verify(root)
        journal = root / "runs/generation/journal.json"
        print(
            json.dumps(
                {
                    "run_id": plan["group"]["run_id"],
                    "journal": read_json(journal) if journal.exists() else None,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
