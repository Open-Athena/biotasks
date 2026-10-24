"""Acquire only immutable task/cache members from the already public #28 phase.

This is a local handoff regression using historical inputs, not a new generation
run and not a native control attempt. No credentials, model or worker are used.
"""

import argparse
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

from biotasks.validation.files import inventory, json_sha, read_json, require, safe, sha, write_json
from biotasks.validation.preservation import transfer_limits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    plan = read_json(args.plan)
    root = args.plan.resolve().parent
    ledger_path, manifest_path = Path(plan["source_ledger"]), Path(plan["source_manifest"])
    require(
        sha(ledger_path) == plan["source_ledger_sha256"]
        and sha(manifest_path) == plan["source_manifest_sha256"],
        "Historical source identity changed",
    )
    review = read_json(Path(plan["public_review"]))
    require(
        review["public_eligible"] and review["repo"] == plan["repo"],
        "Historical source not public eligible",
    )
    manifest, ledger = read_json(manifest_path), read_json(ledger_path)
    phase = next(
        row for row in manifest["files"] if row["path"] == "evidence/phase-artifacts.tar.gz"
    )
    require(phase["bytes"] <= 8 * 1024**2, "Historical archive exceeds bound")
    tasks = [row for row in ledger["tasks"] if row["repo"] == plan["repo"]]
    require(len(tasks) == plan["expected_tasks"], "Historical task count changed")
    slug = plan["repo"].replace("/", "__")
    expected = {
        "outputs/" + slug + "/" + task["task"] + "/" + row["path"]: row
        for task in tasks
        for row in task["original_task_files"]
    }
    specs = {row["path"]: row for row in phase["members"]}
    caches = {
        name
        for name in specs
        if name.startswith("bootstrap/" + slug + "/") and name.endswith("/bootstrap.json")
    }
    require(len(caches) == 1 and set(expected) <= set(specs), "Historical members incomplete")
    output = Path(plan["destination"])
    require(
        not output.exists(), "Historical acquisition already exists; verify it instead of replacing"
    )
    output.mkdir(parents=True, mode=0o700)
    object_path = (
        "research/28-catalogued-fields/"
        + manifest["created_utc"][:10]
        + "/"
        + sha(manifest_path)
        + "/"
        + phase["path"]
    )
    with tempfile.TemporaryDirectory(prefix="download-", dir=output) as temporary:
        temporary = Path(temporary)
        with transfer_limits(temporary):
            from huggingface_hub import HfApi
            from huggingface_hub.utils import disable_progress_bars

            disable_progress_bars()
            archive = temporary / "phase.tar.gz"
            HfApi(token=False).download_bucket_files(
                "open-athena/biotasks",
                [(object_path, archive)],
                raise_on_missing_files=True,
                token=False,
            )
            require(
                archive.stat().st_size == phase["bytes"] and sha(archive) == phase["sha256"],
                "Historical HF object bytes changed",
            )
            seen, total = set(), 0
            with tarfile.open(archive, "r|gz") as stream:
                for member in stream:
                    name = safe(member.name)
                    total += member.size
                    require(total <= 16 * 1024**2, "Expanded historical phase exceeds bound")
                    if name not in expected and name not in caches:
                        continue
                    require(
                        member.isfile() and name not in seen and member.size <= 1024**2,
                        "Invalid historical member",
                    )
                    seen.add(name)
                    raw = stream.extractfile(member).read(1024**2 + 1)
                    spec = specs[name]
                    require(
                        len(raw) == spec["bytes"] == member.size
                        and hashlib.sha256(raw).hexdigest() == spec["sha256"],
                        "Historical member bytes changed",
                    )
                    if name in expected:
                        recorded = expected[name]
                        require(
                            recorded["sha256"] == spec["sha256"]
                            and recorded["mode"] == member.mode,
                            "Historical ledger differs from source",
                        )
                        target = output / "raw" / name.removeprefix("outputs/" + slug + "/")
                    else:
                        target = output / "bootstrap" / name.removeprefix("bootstrap/")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    target.chmod(member.mode)
            require(seen == set(expected) | caches, "Historical extraction incomplete")
    raw_files, cache_files = inventory(output / "raw"), inventory(output / "bootstrap")
    write_json(
        root / "historical-acquisition.json",
        {
            "kind": "historical source-only handoff regression, not fresh generation",
            "source_plan_sha256": sha(args.plan),
            "source_ledger_sha256": sha(ledger_path),
            "source_manifest_sha256": sha(manifest_path),
            "anonymous_download_verified": True,
            "object_path": object_path,
            "object_sha256": phase["sha256"],
            "downloaded_bytes": phase["bytes"],
            "tasks": len(tasks),
            "raw_files": raw_files,
            "raw_inventory_sha256": json_sha(raw_files),
            "cache_files": cache_files,
            "cache_inventory_sha256": json_sha(cache_files),
            "download_cache_removed": True,
            "model_calls": 0,
            "remote_jobs": 0,
        },
    )
    print(
        json.dumps(
            {
                "historical_tasks_acquired": len(tasks),
                "raw_files": len(raw_files),
                "model_calls": 0,
                "remote_jobs": 0,
                "download_verified": True,
            }
        )
    )


if __name__ == "__main__":
    main()
