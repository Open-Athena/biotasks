"""Actual installed CLI/source/export proof, with all external effects forbidden.

Run with the built wheel's interpreter using -I and no -B. Inputs are the known
completed generation, its original local-export baseline and local official
archive/writer bytes. No research runtime module may be imported/read as code.
"""

import argparse
import copy
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import biotasks.generation
from biotasks.cli import main as cli
from biotasks.generation import handoff, resources, source
from biotasks.validation.archives import records
from biotasks.validation.files import (
    inventory, json_sha, read_json, require, sha, write_json,
)
from biotasks.validation.planning import code_identity


def reference(path):
    return {"path": str(path), "sha256": sha(path)}


def call(args):
    stream = io.StringIO()
    with redirect_stdout(stream):
        cli(args)
    return json.loads(stream.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generation", "baseline", "archive", "dependency", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    generation, baseline, archive, dependency, output = [getattr(args, name).resolve() for name in ("generation", "baseline", "archive", "dependency", "output")]
    require(not output.exists(), "Never overwrite proof output")
    require(Path(biotasks.generation.__file__).resolve().is_relative_to(Path(sys.prefix)), "Proof did not import an installed wheel")
    require(sys.dont_write_bytecode is False, "Proof must exercise default bytecode behavior")
    output.mkdir(parents=True, mode=0o700)
    plan = read_json(generation / "plan.json")
    budget = Path(plan["budget_ledger"])
    before = {"generation_inventory_sha256": json_sha(inventory(generation)), "baseline_inventory_sha256": json_sha(inventory(baseline)), "budget_sha256": sha(budget)}
    permitted_data = (generation, baseline, archive, dependency)

    def offline(event, event_args):
        require(event not in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}, "Installed proof attempted an external effect: " + event)
        if event == "open" and isinstance(event_args[0], str):
            path = Path(event_args[0]).resolve()
            name = str(path)
            require(not any(part in name for part in (".codex/secrets/", ".config/gh/", ".config/coreweave/", ".cache/huggingface/token", ".git-credentials", ".docker/config.json")), "Installed proof attempted credential access")
            if "/.research-worktrees/" in name and any(part in name for part in ("/31/", "/44/", "/45/", "/pipeline44-final/", "/pipeline48/src/")):
                require(any(path == allowed or path.is_relative_to(allowed) for allowed in permitted_data), "Installed proof attempted a research-source dependency: " + name)

    sys.addaudithook(offline)
    prepared_source = call(["generate", "prepare-source", str(output / "source-cache"), "--archive", str(archive), "--dependency", str(dependency)])
    source_cache = output / "source-cache"
    receipt = source.verify(source_cache)
    require(len(receipt["source_inventory"]) == 353, "Incomplete actual source acquisition")
    source_before = inventory(source_cache)
    notice_dir = output / "notices"
    for name, row in records(generation / plan["group"]["notices"]["path"], "tar.gz").items():
        target = notice_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(row["data"])
        target.chmod(row["mode"])
    manifest = {
        "schema_version": 1, "id": "wheel48", "repo2rlenv_revision": plan["repo2rlenv_revision"],
        "validation_code_identity": code_identity(), "source": prepared_source["source"],
        "price_quote": reference(generation / "price-quote.json"), "backend": plan["backend"],
        "backend_config": reference(Path(plan["backend"]["config"])), "client_profile": plan["client_profile"],
        "budget_ledger": str(budget), "archive": {"kind": "local"},
        "cases": [{"id": "reference", "mode": "completed", "run_id": plan["group"]["run_id"], "generation_root": str(generation), "generation_plan_sha256": sha(generation / "plan.json"), "native_config": reference(generation / "native-config.json"), "candidates": reference(generation / "reference-candidates.json"), "notices": {"path": str(notice_dir), "inventory_sha256": json_sha(inventory(notice_dir))}, "publication": {"eligible": False}}],
    }
    manifest_file = output / "manifest.json"
    write_json(manifest_file, manifest)
    planned = call(["generate", "plan", str(manifest_file), "--work-dir", str(output / "planned")])
    first = call(["generate", "run", str(output / "planned"), "--once"])
    require(first["state"] == "local_export_prepared", "Installed CLI did not prepare archived export")
    first_files = inventory(output / "planned")
    native = sys.modules["repo2rlenv.registry.integration"]
    native.prepare_dataset_for_push = lambda *a, **k: require(False, "Completed handoff reran exporter")
    second = call(["generate", "run", str(output / "planned"), "--once"])
    require(first == second and first_files == inventory(output / "planned"), "Installed completed handoff was not byte-inert")
    require(source_before == inventory(source_cache) and sys.dont_write_bytecode is False, "Default import behavior mutated source cache or bytecode policy")
    current = output / "planned/reference-handoff/prepared-local/handoff/prepared"
    old_rows, new_rows = inventory(baseline), inventory(current)
    require([row["path"] for row in old_rows] == [row["path"] for row in new_rows], "Prepared member set differs")
    changed = []
    for old, new in zip(old_rows, new_rows, strict=True):
        require(old["mode"] == new["mode"], "Original executable mode changed")
        if old != new:
            changed.append(old["path"])
    require(all(name.endswith("/task.toml") for name in changed), "Prepared executable/source bytes changed")
    for path in current.rglob("task.toml"):
        require(handoff.grading_contract(path) == handoff.grading_contract(baseline / path.relative_to(current)), "Original grading changed")
    # Exercise fresh planning under normal bytecode defaults, never admission.
    fresh = copy.deepcopy(manifest)
    fresh["id"] = "wheel48-fresh"
    case = fresh["cases"][0]
    case["mode"] = "fresh"
    case["run_id"] = "biotasks48-wheel-offline-plan"
    del case["generation_root"], case["generation_plan_sha256"]
    fresh_path = output / "fresh-manifest.json"
    write_json(fresh_path, fresh)
    call(["generate", "plan", str(fresh_path), "--work-dir", str(output / "fresh-plan")])
    require(call(["generate", "run", str(output / "fresh-plan"), "--once"])["state"] == "generation_not_admitted", "Fresh proof admitted execution")
    require(not list((output / "fresh-plan/reference/payload").rglob("__pycache__")), "Fresh payload contains generated bytecode")
    hashes = {**plan["reused_baseline_sha256"], "cost_guard.py": plan["original_cost_guard_sha256"], "generation_entry.py": plan["own_code_sha256"]["generation_entry.py"], "generation_worker.py": plan["own_code_sha256"]["generation_worker.py"]}
    from biotasks.validation.files import content_sha

    require({name: content_sha(raw) for name, raw in resources.assets().items()} == hashes, "Frozen controller assets differ")
    after = {"generation_inventory_sha256": json_sha(inventory(generation)), "baseline_inventory_sha256": json_sha(inventory(baseline)), "budget_sha256": sha(budget)}
    require(before == after and source_before == inventory(source_cache), "Original/source/budget evidence changed")
    result = {"kind": "Actual installed CLI proof; archived generation plus fresh offline planning, no new generation/controls", "installed_module": str(Path(biotasks.generation.__file__).resolve()), "generation_code_identity": resources.code_identity(), "validation_code_identity": code_identity(), "source_receipt_identity": receipt["receipt_identity"], "source_members": len(receipt["source_inventory"]), "source_bytes": sum(row["bytes"] for row in receipt["source_inventory"]), "dependency_members": len(receipt["dependency_inventory"]), "frozen_assets_byte_identical": len(hashes), "manifest_plan_identity": planned["plan_identity"], "result": first, "prepared_members": len(new_rows), "changed_members": changed, "grading_contract_and_all_modes_identical": True, "completed_resume_byte_inert": True, "default_bytecode_policy_restored": True, "source_cache_byte_identical_after_imports": True, "fresh_planning_no_bytecode_or_admission": True, "network_subprocess_credentials_and_research_code_forbidden": True, "before": before, "after": after, "new_model_calls": 0, "new_remote_jobs": 0, "new_spend_usd": 0, "fresh_native_execution_proven": False}
    write_json(output / "proof.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
