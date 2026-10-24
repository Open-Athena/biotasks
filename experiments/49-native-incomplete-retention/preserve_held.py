"""Retain a source-verified native disagreement without changing acceptance.

The original journal stays held. Only its pre-reserved exact-worker cleanup
operation is reused after separate eligible archival and anonymous readback.
"""

import argparse
import json
from pathlib import Path

from biotasks.validation import collection, controller, preservation
from biotasks.validation.archives import records
from biotasks.validation.files import read_json, require, sha, write_json
from biotasks.validation.planning import TOOLS
from log_inspection import review, reviewed_native_logs

ROOT = Path(__file__).resolve().parent


def evidence(original, task_id):
    plan = controller.verify_plan(original)
    group = next(g for g in plan["tasks"] if g["id"] == task_id)
    pipe = controller.Pipeline(original, plan, group)
    directory = pipe.directory
    held = read_json(directory / "held.json")
    require(
        held["stop_verified"] and held["reason"] == "Native reward disagreement",
        "Not a supported held scientific disagreement",
    )
    require(
        sha(directory / "stop/runtime.tar.zst") == held["stop_report_sha256"],
        "Original safety-stop evidence changed",
    )
    report, outer = collection.envelope(
        directory / "runtime.tar.zst",
        read_json(directory / "submission.json"),
        group["payload_sha256"],
        "execute",
        group["run_id"],
    )
    require(
        report.get("stop", {}).get("verified_stopped") is True, "Original execution was not stopped"
    )
    try:
        collection.classify(group, report, outer)
    except ValueError as error:
        require(str(error) == "Native reward disagreement", "Different provenance/collection error")
    else:
        raise ValueError("Native collector did not reject consistency")
    # Input/task/mode/build checks precede that exact error in the pinned
    # collector. Image/wheel checks follow it, so verify those independently.
    builds = [json.loads(s) for s in outer["bounded-builds.jsonl"]["data"].decode().splitlines()]
    images = [json.loads(s) for s in outer["image-identities.jsonl"]["data"].decode().splitlines()]
    require(len(images) == 2, "Incomplete native execution identities")
    for image in images:
        require(
            image["task"] == group["task"]["task"]
            and image["git_head"] == group["task"]["base_commit"],
            "Wrong native checkout",
        )
        prior = [
            b
            for b in builds
            if b["kind"] == "task" and b.get("exit_code") == 0 and b["finished"] < image["captured"]
        ]
        require(
            bool(prior) and prior[-1]["image_id"] == image["image_id"], "Unbound execution image"
        )
    native = json.loads(outer["native-source-parity.json"]["data"])
    require(
        all(
            native[n]["verified"] and native[n]["wheel_sha256"] == TOOLS[n + "_wheel_sha256"]
            for n in ("harbor", "tenacity")
        ),
        "Native wheel source parity missing",
    )
    stop_group = read_json(directory / "stop/group.json")
    stop_report, _ = collection.envelope(
        directory / "stop/runtime.tar.zst",
        read_json(directory / "stop/submission.json"),
        stop_group["payload_sha256"],
        "stop",
        group["run_id"],
    )
    require(
        stop_report.get("stop", {}).get("verified_stopped") is True,
        "Safety stop is not source verified",
    )
    packed = records(outer["control-artifacts.tar.gz"]["data"], "tar.gz")
    approvals = [
        review(group["task"]["task"], name, row["data"])
        for name, row in packed.items()
        if b"\0" in row["data"]
    ]
    require(bool(approvals), "No reviewed native log exception; use an ordinary retention route")
    return pipe, report, outer, approvals


def load(config):
    for row in config["bound_files"]:
        require(sha(Path(row["path"])) == row["sha256"], "Recovery source/evidence changed")
    pipe, report, outer, approvals = evidence(Path(config["original_root"]), config["task_id"])
    require(pipe.plan["plan_identity"] == config["original_plan_identity"], "Original plan changed")
    require(approvals == config["reviewed_native_logs"], "Reviewed native exceptions changed")
    require(pipe.group["publication"]["eligible"] is True, "Original public eligibility missing")
    target = Path(config["output_directory"])
    require(not target.is_relative_to(pipe.root), "Recovery must be separate from original journal")
    target.mkdir(parents=True, exist_ok=True)
    identity = target / "recovery-input.json"
    if identity.exists():
        require(read_json(identity) == config, "Recovery input identity changed")
    else:
        require(not any(target.iterdir()), "Unowned recovery directory")
        write_json(identity, config)
    return pipe, report, outer, approvals, target


def policy(pipe):
    return {
        **pipe.group["publication"],
        "review": pipe.group["publication"]["review"]
        + " Retention-only quarantine: exact source-verified contradictory native logs/rewards; explicitly listed bounded UTF-8 NUL-padded verifier logs are inspected through a non-persisted NUL-free view while original bytes/hashes are retained. No task acceptance or grade repair.",
    }


def prepare(config):
    pipe, report, outer, approvals, target = load(config)
    sources = pipe.publication_sources(
        pipe.directory,
        {
            "original/held.json": pipe.directory / "held.json",
            "original/journal.json": pipe.directory / "journal.json",
            "source/plan.json": pipe.root / "plan.json",
            "recovery/config.json": target / "recovery-input.json",
            "stop/runtime.tar.zst": pipe.directory / "stop/runtime.tar.zst",
            "stop/accounting.json": pipe.directory / "stop/accounting.json",
            "stop/submission.json": pipe.directory / "stop/submission.json",
        },
    )
    manifest = preservation.prepare(
        target,
        sources,
        {
            "run_id": pipe.group["run_id"],
            "operation": "retention-only scientific disagreement",
            "scientific_acceptance": False,
            "native_reward_accepted": False,
            "original_journal_remains_held": True,
            "source_envelope_package_modes_build_image_wheels_stop_verified": True,
            "original_classifier_error": "Native reward disagreement",
            "control_archive_sha256": outer["control-artifacts.tar.gz"]["sha256"],
            "protected_base": report["protected_base"],
            "reviewed_native_logs": approvals,
            "publication_policy": policy(pipe),
            "new_model_calls": 0,
        },
    )
    with reviewed_native_logs(pipe.group["task"]["task"], approvals):
        for row in manifest["files"]:
            preservation.inspect(
                (target / "preserved/files" / row["path"]).read_bytes(), row["path"]
            )
    write_json(ROOT / "primary-archive-manifest.json", manifest)
    return pipe, report, outer, approvals, target


def publish(config):
    pipe, report, outer, approvals, target = prepare(config)
    if (target / "publication.json").exists():
        preservation.verify_receipt(target)
    else:
        with reviewed_native_logs(pipe.group["task"]["task"], approvals):
            preservation.publish(target, pipe.plan["archive"], policy(pipe))
        preservation.verify_receipt(target)
    receipt = read_json(target / "publication.json")
    require(
        receipt.get("anonymous_download_verified") is True, "Anonymous primary readback required"
    )
    write_json(ROOT / "primary-hf-receipt.json", receipt)
    return {"state": "archived_unaccepted", "receipt": receipt, "scientific_acceptance": False}


def cleanup_step(config):
    pipe, report, outer, approvals, target = load(config)
    preservation.verify_receipt(target)
    require(
        read_json(target / "publication.json").get("anonymous_download_verified") is True,
        "Primary readback required before cleanup",
    )
    result_file = target / "result.json"
    if result_file.exists():
        preservation.verify_receipt(target / "cleanup")
        require(
            read_json(result_file)["scientific_acceptance"] is False,
            "Scientific acceptance changed",
        )
        return read_json(result_file)
    intent = {
        "operation": "original pre-reserved cleanup only",
        "run_id": pipe.group["run_id"],
        "original_journal_sha256": sha(pipe.directory / "journal.json"),
        "primary_manifest_sha256": sha(target / "preserved/manifest.json"),
        "primary_publication_sha256": sha(target / "publication.json"),
        "control_archive_sha256": outer["control-artifacts.tar.gz"]["sha256"],
        "protected_base": report["protected_base"],
    }
    file = target / "cleanup-intent.json"
    if file.exists():
        require(read_json(file) == intent, "Recovery cleanup intent changed")
    else:
        write_json(file, intent)
    group, directory, extra = pipe.auxiliary(
        "cleanup",
        archival_verified=True,
        control_archive_sha256=intent["control_archive_sha256"],
        protected_base=report["protected_base"],
    )
    if pipe.ensure_submission(group, directory, **extra) is None:
        return {"state": "pending_original_cleanup_handle", "scientific_acceptance": False}
    account = pipe.observe(group, directory)
    if account is None:
        return {"state": "pending_original_cleanup_terminal", "scientific_acceptance": False}
    raw = collection.download(account, directory, pipe.backend.get("gcloud", "gcloud"))
    final, _ = collection.envelope(
        raw,
        read_json(directory / "submission.json"),
        group["payload_sha256"],
        "cleanup",
        pipe.group["run_id"],
    )
    proof = final.get("cleanup", {})
    require(
        proof.get("verified_empty") is True and not any(proof["remaining"].values()),
        "Owned cleanup unverified; do not resubmit",
    )
    write_json(target / "cleanup-proof.json", proof)
    destination = target / "cleanup"
    destination.mkdir(exist_ok=True)
    sources = pipe.publication_sources(
        directory,
        {
            "cleanup-proof.json": target / "cleanup-proof.json",
            "primary-manifest.json": target / "preserved/manifest.json",
            "primary-publication.json": target / "publication.json",
            "original-held-journal.json": pipe.directory / "journal.json",
            "recovery/cleanup-intent.json": file,
        },
    )
    preservation.prepare(
        destination,
        sources,
        {
            "run_id": pipe.group["run_id"],
            "operation": "retention-only cleanup",
            "scientific_acceptance": False,
            "new_model_calls": 0,
        },
    )
    if (destination / "publication.json").exists():
        preservation.verify_receipt(destination)
    else:
        preservation.publish(destination, pipe.plan["archive"], policy(pipe))
        preservation.verify_receipt(destination)
    require(
        sha(pipe.directory / "journal.json") == intent["original_journal_sha256"],
        "Original held journal changed",
    )
    write_json(ROOT / "cleanup-proof.json", proof)
    write_json(ROOT / "cleanup-hf-receipt.json", read_json(destination / "publication.json"))
    result = {
        "state": "complete",
        "operation": "retention-only recovery",
        "scientific_acceptance": False,
        "native_reward_accepted": False,
        "original_journal": "held and unchanged",
        "original_held_record_is_historical": True,
        "raw_evidence_modified": False,
        "new_validation_or_model_calls": 0,
        "owned_cleanup_verified_empty": True,
        "primary_publication": read_json(target / "publication.json"),
        "cleanup_publication": read_json(destination / "publication.json"),
    }
    write_json(result_file, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "publish", "cleanup-step"])
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    if args.action == "prepare":
        *_, target = prepare(config)
        print(
            json.dumps(
                {
                    "state": "prepared_unaccepted",
                    "manifest_sha256": sha(target / "preserved/manifest.json"),
                }
            )
        )
    else:
        result = publish(config) if args.action == "publish" else cleanup_step(config)
        print(json.dumps(result, indent=2))
