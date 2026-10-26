"""Verify SDK cleanup from an original, fully read-back failure snapshot."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main(number):
    from daytona import Daytona, ListSandboxesQuery

    base = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
    archive = base / f"archives/{number:03}"
    readback = json.loads((archive / "failure-archive-readback.json").read_text())
    snapshot = archive / "snapshot-restored"
    manifest_raw = (snapshot / "snapshot-files.json").read_bytes()
    transport_raw = (snapshot / "transport-export-manifest.json").read_bytes()
    verified = json.loads((snapshot / "snapshot-readback.json").read_text())
    assert verified == readback["snapshot"]
    assert verified["all_snapshot_files_hash_size_mode_verified"] is True
    assert verified["source_manifest_sha256"] == digest(manifest_raw)
    assert verified["transport_manifest_sha256"] == digest(transport_raw)
    manifest = json.loads(manifest_raw)
    assert manifest["source_quiescent"] is True
    entries = {row["path"]: row for row in manifest["files"]}
    assert len(entries) == len(manifest["files"]) == verified["file_count"]
    claim_raw = (base / f"launch/{number:03}-submission.json").read_bytes()
    assert readback["source_claim_sha256"] == digest(claim_raw)
    claim = json.loads(claim_raw)
    assert readback["original_bootstrap_sha256"] == claim["inputs"]["files"]["bootstrap.py"]
    payload = base / f"launch/{number:03}-payload"
    config_raw = (payload / "campaign-config.json").read_bytes()
    assert digest(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
    config = json.loads(config_raw)
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }

    def original(name):
        path = snapshot / "files" / name
        assert not path.is_symlink()
        raw = path.read_bytes()
        row = entries[name]
        assert len(raw) == row["bytes"] and digest(raw) == row["sha256"]
        assert path.stat().st_mode & 0o777 == row["mode"]
        return json.loads(raw), row["sha256"]

    pipeline, _ = original("pipeline.json")
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline["failed_stage"] == "grading"
    assert [row["name"] for row in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
    ]
    assert [row["status"] for row in pipeline["stages"]] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "incomplete",
    ]
    folders = {
        name.removesuffix("/sandbox-claim.json")
        for name in entries
        if name.endswith("/sandbox-claim.json")
    }
    assert folders == {"setup-raw", "replay", "materialization-raw", "grading"}
    evidence, owners = [], []
    for folder in sorted(folders):
        stage, _ = original(folder + "/configuration.json")
        owner = stage["campaign"]
        assert owner.startswith(config["campaign"] + "-")
        owners.append(owner)
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
                "source": "Complete hash/size/mode-verified original quiescent snapshot",
            }
        )
    assert len(owners) == len(set(owners)) == 4
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
    for item in evidence:
        for box in item["sandboxes"]:
            try:
                provider.get(box["id"], request_timeout=30)
            except Exception as error:
                if type(error).__name__ != "DaytonaNotFoundError":
                    raise
            else:
                raise RuntimeError("Original sandbox remains")
    for owner in owners:
        assert not list(
            provider.list(ListSandboxesQuery(labels={"repo2rlenv.job": owner}), request_timeout=30)
        ), "Owned sandbox remains"
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "complete": True,
        "owners": owners,
        "sandboxes": [],
        "original_cleanup_evidence": evidence,
        "original_all_cleanup_passed": True,
        "fresh_original_ids_absent": True,
        "source_configuration_sha256": digest(config_raw),
        "source_archive_format": "quiescent-tar-v1",
        "source_snapshot_manifest_sha256": digest(manifest_raw),
        "source_transport_manifest_sha256": digest(transport_raw),
        "ordinary_autonomous_export_seal_reconstructed": False,
        "scope": "Original snapshot cleanup plus fresh exact ID/owner absence; no scientific acceptance.",
    }
    raw = (json.dumps(result, indent=2) + "\n").encode()
    observations = archive / "cleanup-observations"
    observations.mkdir(exist_ok=True)
    (observations / (digest(raw) + ".json")).write_bytes(raw)
    path = archive / "fresh-provider-cleanup.json"
    assert not path.exists(), "Keep any earlier observation separately"
    path.write_bytes(raw)
    assert path.read_bytes() == raw
    print(json.dumps({"campaign": number, "owners_verified_absent": 4, "complete": True}))


if __name__ == "__main__":
    main(int(sys.argv[1]))
