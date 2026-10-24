"""Exercise the manifest against actual completed45, entirely offline.

This evidence recipe does not discover PRs, regenerate, or execute controls. The
general interface is manifest_flow; absolute paths below identify this proof's
already recorded inputs, not a new repository-selection policy.
"""

import argparse
import sys
from pathlib import Path

import manifest_flow as flow
from biotasks.validation import planning
from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[3]
REFERENCE = BASE / ".research-worktrees/45/experiments/45-generation-handoff"


def ref(path):
    return {"path": str(path), "sha256": sha(path)}


def directory(path):
    return {"path": str(path), "inventory_sha256": json_sha(inventory(path))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), "Never overwrite proof evidence")
    output.mkdir(parents=True, mode=0o700)
    generation = REFERENCE / "inputs-private/generation-002"
    native_plan = read_json(generation / "plan.json")
    recorded_source = read_json(REFERENCE / "historical-handoff-config.json")
    infrastructure = BASE / "experiments/28-catalogued-fields"
    notices = (
        BASE
        / ".research-worktrees/44/experiments/44-validation-entrypoint/inputs-private/opencobra__cobrapy/notices"
    )
    manifest = {
        "schema_version": 1,
        "id": "issue48-archived",
        "repo2rlenv_revision": planning.UPSTREAM,
        "validation_code_identity": planning.code_identity(),
        "adapter": {
            "directory": str(REFERENCE),
            "files": {name: sha(REFERENCE / name) for name in flow.ADAPTER_FILES},
        },
        "infrastructure": {
            name: ref(
                infrastructure / ("history-wide/cost_guard.py" if name == "cost_guard.py" else name)
            )
            for name in flow.ASSETS
        },
        "source": {
            "directory": directory(Path(recorded_source["upstream_source"])),
            "acquisition": ref(Path(recorded_source["upstream_manifest"])),
            "extra_modules": directory(Path(recorded_source["upstream_extra_modules"])),
        },
        "price_quote": ref(generation / "price-quote.json"),
        "backend": native_plan["backend"],
        "backend_config": ref(Path(native_plan["backend"]["config"])),
        "client_profile": native_plan["client_profile"],
        "budget_ledger": native_plan["budget_ledger"],
        "archive": {"kind": "local"},
        "cases": [
            {
                "id": "cobrapy-reference",
                "mode": "completed",
                "run_id": native_plan["group"]["run_id"],
                "generation_root": str(generation),
                "generation_plan_sha256": sha(generation / "plan.json"),
                "native_config": ref(generation / "native-config.json"),
                "candidates": ref(generation / "reference-candidates.json"),
                "notices": directory(notices),
                "publication": {"eligible": False},
            }
        ],
    }
    path = output / "manifest.json"
    write_json(path, manifest)
    budgets = Path(manifest["budget_ledger"])
    before = {
        "generation_inventory_sha256": json_sha(inventory(generation)),
        "budget_sha256": sha(budgets),
    }

    # Global proof guard includes SDK fingerprinting, model transport, credentials
    # and arbitrary child processes, in addition to the exporter's own guard.
    def offline(event, args):
        require(
            event not in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"},
            "Proof attempted external operation: " + event,
        )
        if event == "open" and isinstance(args[0], str):
            require(
                not any(
                    part in str(Path(args[0]).resolve())
                    for part in (
                        ".codex/secrets/",
                        ".config/gh/",
                        ".config/coreweave/",
                        ".cache/huggingface/token",
                        ".git-credentials",
                        ".docker/config.json",
                    )
                ),
                "Proof attempted credential read",
            )

    sys.addaudithook(offline)
    prepared = flow.prepare(path, output / "planned")
    first = flow.advance(path, output / "planned")
    require(first["state"] == "local_export_prepared", "Expected actual archived local export")
    first_inventory = inventory(output / "planned")
    second = flow.advance(path, output / "planned")
    require(
        first == second and first_inventory == inventory(output / "planned"),
        "Completed local handoff is not byte-inert",
    )
    after = {
        "generation_inventory_sha256": json_sha(inventory(generation)),
        "budget_sha256": sha(budgets),
    }
    require(before == after, "Original generation or shared accounting changed")
    result = {
        "kind": "Actual archived45 source-bound offline manifest/handoff proof, not fresh generation or controls",
        "manifest_sha256": sha(path),
        "manifest_plan_identity": prepared["plan_identity"],
        "result": first,
        "before": before,
        "after": after,
        "completed_resume_byte_inert": True,
        "network_subprocess_and_credential_access_forbidden": True,
        "new_model_calls": 0,
        "new_remote_jobs": 0,
        "new_spend_usd": 0,
        "historical_oracle_outcome_not_changed": True,
    }
    write_json(output / "proof.json", result)
    print(__import__("json").dumps(result, indent=2))


if __name__ == "__main__":
    main()
