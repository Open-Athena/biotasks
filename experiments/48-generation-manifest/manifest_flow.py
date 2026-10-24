"""Experimental declarative official-generation planner; no discovery or repair.

Planning is offline and never admits a job. Execution uses the unchanged source-
bound reference adapter and its existing accounting/intent/cleanup contracts.
"""

import argparse
import importlib
import importlib.util
import json
import os
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

from biotasks.validation import planning
from biotasks.validation.archives import pack
from biotasks.validation.files import inventory, json_sha, lock, read_json, require, sha, write_json

ROOT = Path(__file__).resolve().parent
ADAPTER_FILES = (
    "run_generation.py",
    "generation_entry.py",
    "generation_worker.py",
    "generation_client.py",
    "generation_bridge.py",
    "generation_pipeline.py",
    "generation_publication.py",
    "model_budget.py",
    "handoff.py",
    "finish_generation.py",
)
ASSETS = (
    "native_docker.py",
    "setup_controller.sh",
    "observed_cli.py",
    "provider_usage.py",
    "pins.json",
    "cost_guard.py",
)
RESOURCES = {
    "cpus": 4,
    "memory_gib": 16,
    "disk_gib": 30,
    "timeout_seconds": 5400,
    "work_deadline_seconds": 5000,
    "maximum_cpu_hours": 6,
    "cleanup_cpu_hours": 1 / 6,
}
LLM = {
    "provider": "openrouter",
    "model": "anthropic/claude-sonnet-4.6",
    "api_key_env": "OPENROUTER_API_KEY",
    "fallback": None,
}
BOOTSTRAP = {
    "max_iterations": 20,
    "max_seconds": 1800,
    "max_llm_spend_usd": 5.0,
    "cache_dir": "./workspace/bootstrap",
}


def identifier(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value),
        "Invalid fixed identity",
    )
    return value


def file_ref(value):
    path = Path(value["path"])
    require(
        path.is_absolute() and path.is_file() and not path.is_symlink(),
        "Missing absolute input file",
    )
    require(sha(path) == value["sha256"], "Declared input changed: " + str(path))
    return path


def directory_ref(value):
    path = Path(value["path"])
    require(
        path.is_absolute() and json_sha(inventory(path)) == value["inventory_sha256"],
        "Declared directory changed",
    )
    return path


def load(path):
    manifest = read_json(path)
    require(
        manifest["schema_version"] == 1 and manifest["repo2rlenv_revision"] == planning.UPSTREAM,
        "Unsupported manifest/source",
    )
    identifier(manifest["id"])
    require(
        manifest["validation_code_identity"] == planning.code_identity(),
        "Validation implementation changed",
    )
    runtime = manifest["adapter"]
    require(set(runtime["files"]) == set(ADAPTER_FILES), "Incomplete adapter source binding")
    for name, digest in runtime["files"].items():
        file_ref({"path": str(Path(runtime["directory"]) / name), "sha256": digest})
    require(set(manifest["infrastructure"]) == set(ASSETS), "Incomplete infrastructure binding")
    for ref in manifest["infrastructure"].values():
        file_ref(ref)
    source = manifest["source"]
    acquisition = read_json(file_ref(source["acquisition"]))
    require(acquisition["revision"] == planning.UPSTREAM, "Acquisition revision changed")
    source_root = directory_ref(source["directory"])
    # The original acquisition binds the entire official source, not just imports.
    for row in acquisition["files"]:
        target = source_root / row["path"]
        require(target.resolve().is_relative_to(source_root.resolve()), "Unsafe acquisition path")
        file_ref({"path": str(target), "sha256": row["sha256"]})
    directory_ref(source["extra_modules"])
    file_ref(manifest["price_quote"])
    file_ref(manifest["backend_config"])
    require(
        manifest["backend_config"]["path"] == manifest["backend"]["config"],
        "Backend config differs",
    )
    require(manifest["backend"]["type"] == "iris", "Only approved reserved Iris backend")
    require(Path(manifest["budget_ledger"]).is_absolute(), "Absolute shared budget ledger required")
    require(manifest["archive"]["kind"] in {"local", "hf-public"}, "Unsupported archive")
    cases = manifest["cases"]
    require(isinstance(cases, list) and 1 <= len(cases) <= 10, "Manifest case bound is 1..10")
    ids, runs = set(), set()
    for case in cases:
        identity = identifier(case["id"])
        require(identity not in ids, "Duplicate case identity")
        ids.add(identity)
        run_id = identifier(case["run_id"])
        require(run_id not in runs, "Duplicate fixed run identity")
        runs.add(run_id)
        native = read_json(file_ref(case["native_config"]))
        candidates = read_json(file_ref(case["candidates"]))
        require(
            native["pipeline"]["name"] == "pr_runtime"
            and native["llm"] == LLM
            and native["bootstrap"] == BOOTSTRAP,
            "Unapproved native settings",
        )
        require(
            native["auth"] == {"use_gh_cli": False, "use_hf_cli": False}
            and native["output"]["destination"] == "/work/outputs/raw",
            "Native auth/output contract changed",
        )
        require(
            native["repo"]["access"] == "public"
            and re.fullmatch(r"[0-9a-f]{40}", native["repo"]["ref"]),
            "Pinned public repository required",
        )
        require(
            re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", candidates["repo"])
            and native["repo"]["url"] == "https://github.com/" + candidates["repo"],
            "Repository binding differs",
        )
        require(
            candidates["upstream_revision"] == planning.UPSTREAM, "Candidate listing source changed"
        )
        require(
            native["pipeline"]["options"]
            == {key: candidates[key] for key in ("limit", "since", "until")},
            "Frozen discovery options differ",
        )
        rows = candidates["candidates"]
        require(
            isinstance(rows, list) and 0 <= len(rows) <= candidates["limit"] <= 100,
            "Candidate batch bound exceeded",
        )
        require(len({row["number"] for row in rows}) == len(rows), "Duplicate PR identity")
        for row in rows:
            require(
                row["state"] == "MERGED"
                and all(re.fullmatch(r"[0-9a-f]{40}", row[k]) for k in ("base_sha", "head_sha")),
                "Only frozen merged PR descriptors",
            )
        directory_ref(case["notices"])
        policy = case["publication"]
        require(isinstance(policy["eligible"], bool), "Explicit publication decision required")
        require(
            not policy["eligible"] or bool(policy.get("review")),
            "Public eligibility review required",
        )
        require(case["mode"] in {"fresh", "completed"}, "Unsupported generation mode")
        if case["mode"] == "completed":
            root = Path(case["generation_root"])
            file_ref({"path": str(root / "plan.json"), "sha256": case["generation_plan_sha256"]})
    return manifest


def adapter(manifest):
    """Load only explicitly bound local code; refuse same-named foreign imports."""
    directory = Path(manifest["adapter"]["directory"]).resolve()
    sys.path.insert(0, str(directory))
    for name in ("run_generation", "finish_generation", "handoff"):
        module = importlib.import_module(name)
        require(
            Path(module.__file__).resolve() == directory / (name + ".py"),
            "Adapter import came from another installation",
        )
    return sys.modules["run_generation"], sys.modules["finish_generation"], sys.modules["handoff"]


def _fresh(manifest, case, root, runtime, context):
    root.mkdir()
    payload = root / "payload"
    payload.mkdir()
    quote = read_json(file_ref(manifest["price_quote"]))
    policy_source = file_ref(manifest["infrastructure"]["cost_guard.py"])
    spec = importlib.util.spec_from_file_location("manifest_cost_guard", policy_source)
    pricing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pricing)
    model = {
        "maximum_usd": str(pricing.reservation(quote, 2048) + Decimal(5)),
        "quote_sha256": manifest["price_quote"]["sha256"],
        "actual_stop_usd": "5",
        "only_original_upstream_calls": True,
    }
    shutil.copyfile(file_ref(manifest["price_quote"]), root / "price-quote.json")
    reused = {}
    for name, ref in manifest["infrastructure"].items():
        shutil.copyfile(file_ref(ref), payload / name)
        if name != "cost_guard.py":
            reused[name] = ref["sha256"]
    for name in ("generation_entry.py", "generation_worker.py"):
        shutil.copyfile(Path(manifest["adapter"]["directory"]) / name, payload / name)
    for name, data in planning.code_files().items():
        target = payload / "biotasks/validation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (payload / "biotasks/__init__.py").write_text("")
    shutil.copyfile(
        file_ref(manifest["source"]["acquisition"]), payload / "upstream-source-manifest.json"
    )
    for key, name in (
        ("native_config", "native-config.json"),
        ("candidates", "reference-candidates.json"),
    ):
        shutil.copyfile(file_ref(case[key]), payload / name)
        shutil.copyfile(file_ref(case[key]), root / name)
    write_json(payload / "model-run-budget.json", model)
    write_json(
        payload / "family.json",
        {
            "run_id": case["run_id"],
            "operation": "generate",
            "network": manifest["backend"]["network"],
            "tools": planning.TOOLS,
            "resources": RESOURCES,
            "model_budget": model,
        },
    )
    write_json(
        payload / "payload.json",
        {
            "run_id": case["run_id"],
            "sha256": {
                p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
            },
        },
    )
    package = pack(Path(case["notices"]["path"]), root / "notices.tar.gz")
    package["path"] = "notices.tar.gz"
    plan = {
        "schema_version": 1,
        "kind": "official generation lifecycle, not native validation",
        "repo2rlenv_revision": planning.UPSTREAM,
        "backend": manifest["backend"],
        "backend_config_sha256": manifest["backend_config"]["sha256"],
        "client_profile": manifest["client_profile"],
        "budget_ledger": manifest["budget_ledger"],
        "archive": manifest["archive"],
        "validation_code_identity": planning.code_identity(),
        "own_code_sha256": {name: manifest["adapter"]["files"][name] for name in runtime.OWN_CODE},
        "model_budget": model,
        "reused_baseline_sha256": reused,
        "original_cost_guard_sha256": sha(policy_source),
        "group": {
            "id": "generation",
            "run_id": case["run_id"],
            "resources": RESOURCES,
            "payload_directory": "payload",
            "payload_sha256": {
                p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
            },
            "notices": package,
            "publication": case["publication"],
        },
        "new_capacity_allowed": False,
        "task_repairs": False,
        "admission_state": "not admitted; offline manifest planning",
        "manifest_interface": {"binding": context, "case": case},
    }
    plan["plan_identity"] = json_sha(plan)
    write_json(root / "plan.json", plan)
    runtime.verify(root)


def binding(path, manifest):
    return {
        "manifest": str(path.resolve()),
        "manifest_sha256": sha(path),
        "validation_code_identity": planning.code_identity(),
        "implementation_sha256": {
            name: sha(ROOT / name) for name in ("manifest_flow.py", "manifest_handoff.py")
        },
        "id": manifest["id"],
    }


def verify(path, output):
    manifest = load(path)
    frozen = read_json(output / "manifest-plan.json")
    original = dict(frozen)
    require(original.pop("plan_identity") == json_sha(original), "Frozen manifest plan changed")
    require(
        frozen["binding"] == binding(path, manifest), "Manifest/implementation identity changed"
    )
    require(frozen["manifest"] == manifest, "Frozen manifest changed")
    return manifest, frozen


def prepare(path, output):
    manifest = load(path)
    runtime, _, _ = adapter(manifest)
    protected = [
        Path(manifest["adapter"]["directory"]),
        Path(manifest["source"]["directory"]["path"]),
        Path(manifest["source"]["extra_modules"]["path"]),
    ]
    protected.extend(Path(case["notices"]["path"]) for case in manifest["cases"])
    protected.extend(
        Path(case["generation_root"]) for case in manifest["cases"] if case["mode"] == "completed"
    )
    require(
        all(
            not output.resolve().is_relative_to(root.resolve())
            and not root.resolve().is_relative_to(output.resolve())
            for root in protected
        ),
        "Output overlaps protected source/evidence",
    )
    if output.exists():
        return verify(path, output)[1]
    staging = output.with_name(output.name + ".staging")
    # A preparation interrupted before atomic publication has no effect/admission.
    # Keep it for inspection rather than interpreting it as an executable plan.
    require(not staging.exists(), "Interrupted planning staging exists; inspect before removing")
    staging.mkdir(parents=True, mode=0o700)
    cases = []
    for case in manifest["cases"]:
        candidates = read_json(file_ref(case["candidates"]))["candidates"]
        row = {
            "id": case["id"],
            "mode": case["mode"],
            "candidate_count": len(candidates),
            "all_repository_prs_covered": False,
        }
        if case["mode"] == "completed":
            old = runtime.verify(Path(case["generation_root"]))
            require(old["group"]["run_id"] == case["run_id"], "Imported run identity differs")
            require(
                sha(Path(case["generation_root"]) / "native-config.json")
                == case["native_config"]["sha256"]
                and sha(Path(case["generation_root"]) / "reference-candidates.json")
                == case["candidates"]["sha256"],
                "Imported native inputs differ",
            )
            row["state"] = "imported_existing_generation"
        elif not candidates:
            row["state"] = "skipped_zero_candidates"
        else:
            _fresh(manifest, case, staging / case["id"], runtime, binding(path, manifest))
            row["state"] = "prepared_not_admitted"
        cases.append(row)
    value = {
        "binding": binding(path, manifest),
        "manifest": manifest,
        "cases": cases,
        "planning_model_calls": 0,
        "planning_remote_jobs": 0,
        "serial_execution": True,
    }
    value["plan_identity"] = json_sha(value)
    write_json(staging / "manifest-plan.json", value)
    os.replace(staging, output)
    return verify(path, output)[1]


def advance(path, output, *, allow_generation=False, allow_validation=False):
    """One serial pass. An incomplete/held case prevents admission of the next."""
    manifest, frozen = verify(path, output)
    runtime, finish, _ = adapter(manifest)
    from biotasks.validation import controller
    from manifest_handoff import prepare_handoff

    with lock(output / "advance.lock"):
        results = []
        for case, planned in zip(manifest["cases"], frozen["cases"], strict=True):
            if planned["state"] == "skipped_zero_candidates":
                results.append(
                    {
                        "id": case["id"],
                        "state": "zero_candidates",
                        "model_calls": 0,
                        "native_jobs": 0,
                    }
                )
                continue
            generation = (
                Path(case["generation_root"])
                if case["mode"] == "completed"
                else output / case["id"]
            )
            if case["mode"] == "fresh":
                if not allow_generation:
                    return {
                        "state": "generation_not_admitted",
                        "case": case["id"],
                        "results": results,
                    }
                state = runtime.run(generation, once=True)
                if state["state"] != "complete":
                    return {"state": state["state"], "case": case["id"], "results": results}
            ready = finish.generation_ready(generation)
            if ready["state"] != "ready":
                return {"state": ready["state"], "case": case["id"], "results": results}
            result = prepare_handoff(manifest, case, ready, output / (case["id"] + "-handoff"))
            if result["state"] == "zero_exports":
                results.append({"id": case["id"], **result})
                continue
            if not allow_validation:
                return {
                    "state": "local_export_prepared",
                    "case": case["id"],
                    "results": results,
                    "handoff": result,
                }
            validation = output / (case["id"] + "-handoff") / "validation"
            if not validation.exists():
                planning.prepare(Path(result["validation_manifest"]), validation)
            else:
                controller.verify_plan(validation)
            state = controller.run(validation, once=True)
            if state["state"] != "complete":
                return {"state": state["state"], "case": case["id"], "results": results}
            results.append(
                {
                    "id": case["id"],
                    "state": "validation_workflow_complete",
                    "scientific_acceptance": "read individual immutable control readbacks",
                    "validation": state,
                }
            )
        return {
            "state": "workflow_complete",
            "results": results,
            "new_unique_task_count": "not inferred from exports",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "verify", "advance"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-generation", action="store_true")
    parser.add_argument("--allow-validation", action="store_true")
    args = parser.parse_args()
    path, output = args.manifest.resolve(), args.output.resolve()
    if args.action == "plan":
        result = prepare(path, output)
    elif args.action == "verify":
        result = verify(path, output)[1]
    else:
        result = advance(
            path,
            output,
            allow_generation=args.allow_generation,
            allow_validation=args.allow_validation,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
