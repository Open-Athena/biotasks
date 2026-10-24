"""Exercise the unmodified actor against a real archived hold and frozen backend.

Offline preparation forbids all transport and credential reads. Publication
permits only the existing HF preservation path; no native client or subprocess
may run. Neither mode changes the source plan, accounting or scientific state.
"""

import argparse
import json
import sys
from pathlib import Path

import retain
from biotasks.validation import budget, controller, preservation
from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("offline", "publish"))
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--reviewed-reference", type=Path, required=True)
    args = parser.parse_args()
    original, output = args.original.resolve(), args.output.resolve()

    def deny(*unused, **kwargs):
        raise AssertionError("Archived proof must not invoke native/model transport")

    controller.Pipeline.client = deny

    def audit(event, values):
        if event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}:
            deny()
        if args.action == "offline":
            if event in {"socket.connect", "socket.getaddrinfo"}:
                deny()
            if event == "open" and isinstance(values[0], (str, bytes)):
                name = str(values[0])
                if any(
                    part in name
                    for part in (
                        "/.codex/secrets/",
                        "/.config/coreweave/",
                        "/.cache/huggingface/token",
                    )
                ):
                    deny()

    sys.addaudithook(audit)
    source_before = inventory(original)
    source_plan = controller.verify_plan(original)
    ledger = Path(source_plan["budget_ledger"])
    budget_before = sha(ledger)
    plan = retain.prepare(original, output, args.prefix)
    states = []
    for _ in range(25):
        state = retain.run(output, publish=args.action == "publish", cleanup=False)
        states.append(state["state"])
        if state["state"].startswith("pending:") or state["state"] == "retention_complete":
            break
    expected = (
        "pending:publication_resolved:public transfer not admitted"
        if args.action == "offline"
        else "retention_complete"
    )
    require(state["state"] == expected, "Unexpected archived proof outcome")
    require(inventory(original) == source_before, "Original evidence changed")
    require(sha(ledger) == budget_before, "Original cumulative budget changed")
    cases = []
    reviewed = read_json(args.reviewed_reference)["reviewed_native_logs"]
    expected_views = [
        {key: row[key] for key in ("path", "bytes", "sha256", "nul_bytes")} for row in reviewed
    ]
    for task_id in plan["task_ids"]:
        directory = output / "cases" / task_id
        source = read_json(directory / "source.json")
        actual_views = [
            {key: row[key] for key in ("path", "bytes", "sha256", "nul_bytes")}
            for row in source["inspection_views"]
        ]
        require(
            actual_views == expected_views,
            "Automatically derived views differ from reviewed original bytes",
        )
        manifest = preservation.verify(directory)
        cases.append(
            {
                "task_id": task_id,
                "source_identity": source["source_identity"],
                "original_files_sha256": source["original_files_sha256"],
                "inspection_views": source["inspection_views"],
                "manifest_sha256": sha(directory / "preserved/manifest.json"),
                "files": manifest["files"],
                "native_controls": source["native_controls"],
            }
        )
    if args.action == "publish":
        before = inventory(output)
        preservation.publish = deny
        budget.reconcile = deny
        require(retain.run(output) == state, "Completed replay changed result")
        require(inventory(output) == before, "Completed replay changed sidecar bytes")
        require(
            inventory(original) == source_before and sha(ledger) == budget_before,
            "Completed replay changed original evidence/accounting",
        )
    proof = {
        "action": args.action,
        "retention_plan_identity": plan["plan_identity"],
        "implementation_sha256": retain.implementation(),
        "installed_validation_path": str(Path(controller.__file__).resolve()),
        "states": states,
        "result": state,
        "cases": cases,
        "source_inventory_sha256": json_sha(source_before),
        "source_inventory_files": len(source_before),
        "original_cumulative_budget_sha256": budget_before,
        "original_source_and_budget_unchanged": True,
        "unmodified_backend_and_publication_policy": True,
        "native_model_subprocess_transport_forbidden": True,
        "offline_network_and_credentials_forbidden": args.action == "offline",
        "completed_replay_byte_inert": args.action == "publish",
        "reviewed_log_hashes_used_as_actor_inputs": False,
        "new_native_jobs_or_model_calls": 0,
        "scientific_acceptance": False,
    }
    write_json(args.proof, proof)
    print(
        json.dumps(
            {
                "proof": str(args.proof),
                "sha256": sha(args.proof),
                "states": states,
                "scientific_acceptance": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
