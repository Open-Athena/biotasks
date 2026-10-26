"""Verify regular-archive cleanup, including every created SDK claim ID.

Derived from the retained operator v2 verifier; reuse the tested pure claim-ID
checker. Empty SDK cleanup lists do not hide their creation claims. For completed
native jobs, verify the executed ownership label and the final absence query;
Harbor may already have deleted the environment before supervisor cleanup. Do not
infer an unrecorded native ID. This supplies neither science nor cost acceptance.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from verify_snapshot_cleanup import verify_claim_ids_absent


def check_native_ownership(record):
    """A completed native job may have no ID left for supervisor cleanup."""
    assert record["state"] == "completed" and record["returncode"] == 0
    assert record["cleanup"]["passed"] and not record["cleanup"].get("creation_uncertain")
    command = record["command"]
    labels = [
        json.loads(arg.removeprefix("labels="))
        for index, arg in enumerate(command)
        if index and command[index - 1] == "--ek" and arg.startswith("labels=")
    ]
    assert labels == [{"repo2rlenv.job": record["job_id"]}]
    return record["job_id"]


def main():
    from daytona import Daytona, ListSandboxesQuery

    base = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
    token = subprocess.run(
        [
            "/home/exedev/.local/google-cloud-sdk/bin/gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret",
            "DAYTONA_EVAL_API_KEY",
            "--project",
            "hai-gcp-models",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    os.environ["DAYTONA_API_KEY"] = token
    provider = Daytona()
    for number in map(int, sys.argv[1:]):
        archive = base / f"archives/{number:03}"
        root = archive / "files"
        readback = json.loads((archive / "independent-readback.json").read_text())
        assert readback["all_files_download_verified"]
        entries = {
            row["path"]: row
            for row in json.loads((archive / "sealed-manifest.json").read_text())["files"]
        }

        def original(name, root=root, entries=entries):
            raw = (root / name).read_bytes()
            row = entries[name]
            assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
            return json.loads(raw), row["sha256"]

        pipeline, _ = original("pipeline.json")
        assert pipeline["status"] in {"validated", "rejected", "infrastructure_failed"}
        claim = json.loads((base / f"launch/{number:03}-submission.json").read_text())
        expected_hash = claim["inputs"]["files"]["campaign-config.json"]
        configurations = [
            path
            for path in (base / "launch").glob(f"{number:03}-payload*/campaign-config.json")
            if hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
        ]
        assert configurations, "No original submission-bound configuration"
        config = json.loads(configurations[0].read_text())
        resources = config["task_policy"]["sandbox"]
        assert resources == {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False}
        mapping = {
            "setup": "setup-raw",
            "replay": "replay",
            "construction": "materialization-raw",
            "grading": "grading",
        }
        folders = [mapping[row["name"]] for row in pipeline["stages"] if row["name"] in mapping]
        # Every SDK sandbox claim in the sealed archive must have its own cleanup.
        # This includes optional construction and grading repair sessions.
        claimed_folders = {
            name.rsplit("/", 1)[0] for name in entries if name.endswith("/sandbox-claim.json")
        }
        assert all(
            folder + "/configuration.json" in entries and folder + "/cleanup.json" in entries
            for folder in claimed_folders
        )
        for folder in sorted(claimed_folders):
            if folder not in folders:
                folders.append(folder)
        owners = []
        sdk_claims = []
        native_unrecorded = []
        evidence = []
        for folder in folders:
            stage_config, _ = original(folder + "/configuration.json")
            owner = stage_config["campaign"]
            assert owner.startswith(config["campaign"] + "-")
            owners.append(owner)
            sdk_claim, _ = original(folder + "/sandbox-claim.json")
            assert sdk_claim["owner"] == owner
            assert sdk_claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
            sdk_claims.append(sdk_claim)
            cleanup, sha = original(folder + "/cleanup.json")
            assert cleanup["passed"] and not cleanup["remaining"]
            assert not cleanup.get("creation_uncertain")
            assert all(
                box["deleted"] and (box["cpu"], box["memory"], box["disk"]) == (4, 8, 10)
                for box in cleanup["sandboxes"]
            )
            evidence.append(
                {
                    "path": folder + "/cleanup.json",
                    "sha256": sha,
                    "cleanup_verified": True,
                    "sandboxes": cleanup["sandboxes"],
                    "source": "complete hash-verified original archive",
                }
            )
        if any(row["name"] == "native" for row in pipeline["stages"]):
            native, _ = original("native/execution.json")
            assert native["task_resources"] == {"cpus": 4, "memory_mb": 8192, "storage_mb": 10240}
            records = sorted((root / "native").glob("*/remote-job.json"))
            assert len(records) == 3
            for path in records:
                relative = path.relative_to(root).as_posix()
                record, sha = original(relative)
                cleanup = record["cleanup"]
                check_native_ownership(record)
                if not cleanup["sandboxes"]:
                    native_unrecorded.append(record["job_id"])
                assert cleanup["passed"] and not cleanup.get("creation_uncertain")
                assert all(
                    box["deleted"] and (box["cpu"], box["memory"], box["disk"]) == (4, 8, 10)
                    for box in cleanup["sandboxes"]
                )
                owners.append(record["job_id"])
                evidence.append(
                    {
                        "path": relative,
                        "sha256": sha,
                        "cleanup_verified": True,
                        "sandboxes": cleanup["sandboxes"],
                        "source": "complete hash-verified original archive",
                    }
                )
        assert len(owners) == len(set(owners))
        verify_claim_ids_absent(provider, sdk_claims)
        checked_sdk_ids = {claim["id"] for claim in sdk_claims}
        for item in evidence:
            for box in item["sandboxes"]:
                if box["id"] in checked_sdk_ids:
                    continue
                try:
                    provider.get(box["id"], request_timeout=30)
                except Exception as error:
                    if type(error).__name__ != "DaytonaNotFoundError":
                        raise
                else:
                    raise RuntimeError("Original sandbox remains")
        for owner in owners:
            assert not list(
                provider.list(
                    ListSandboxesQuery(labels={"repo2rlenv.job": owner}), request_timeout=30
                )
            ), "Owned sandbox remains"
        result = {
            "observed_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "owners": owners,
            "sandboxes": [],
            "original_cleanup_evidence": evidence,
            "original_all_cleanup_passed": True,
            "fresh_original_ids_absent": True,
            "all_original_sdk_claim_ids_checked": True,
            "original_sdk_claims": sdk_claims,
            "native_unrecorded_id_owners": native_unrecorded,
            "source_configuration_sha256": expected_hash,
            "source_archive_manifest_sha256": hashlib.sha256(
                (archive / "sealed-manifest.json").read_bytes()
            ).hexdigest(),
            "scope": "Every original SDK creation ID and any recorded native cleanup ID checked directly; completed native jobs bind their executed owner labels to fresh owner-absence queries. No unrecorded native ID inferred; native acceptance checked separately",
        }
        destination = base / f"archives/{number:03}/fresh-provider-cleanup.json"
        observations = archive / "cleanup-observations"
        observations.mkdir(exist_ok=True)
        if destination.exists():
            prior = destination.read_bytes()
            prior_path = observations / (hashlib.sha256(prior).hexdigest() + ".json")
            if prior_path.exists():
                assert prior_path.read_bytes() == prior
            else:
                prior_path.write_bytes(prior)
            assert prior_path.read_bytes() == prior
        data = (json.dumps(result, indent=2) + "\n").encode()
        observation = observations / (hashlib.sha256(data).hexdigest() + ".json")
        if observation.exists():
            assert observation.read_bytes() == data
        else:
            observation.write_bytes(data)
        assert observation.read_bytes() == data
        destination.write_bytes(data)
        print(
            json.dumps(
                {
                    "campaign": number,
                    "original_cleanup_verified": len(evidence),
                    "owners_checked": len(owners),
                    "remaining_sandboxes": 0,
                    "submission_bound_config": True,
                }
            )
        )


if __name__ == "__main__":
    main()
