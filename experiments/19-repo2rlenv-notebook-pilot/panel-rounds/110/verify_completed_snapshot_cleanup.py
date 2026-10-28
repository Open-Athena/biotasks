"""Check completed snapshot resources, including a permitted comparison repair.

Operator-only readback. Reuses original snapshot verification and the existing
claim-ID, bounded SDK-topology and native-owner checks. This cannot accept a
scientific task, allocate resources, change a worker or reconcile its cost.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/101"))
from snapshot_archive import verify_snapshot_archive  # noqa: E402
from verify_regular_cleanup import check_native_ownership  # noqa: E402
from verify_snapshot_cleanup import verify_claim_ids_absent, verify_sdk_inventory  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def collect_cleanup(snapshot, config):
    """Collect every original SDK claim and all three dispatched native owners."""
    pipeline = snapshot.read_json("pipeline.json")
    assert pipeline["status"] == "validated" and pipeline["autonomous"] is True
    assert pipeline["operator_interventions"] == 0
    assert [row["name"] for row in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
        "native",
    ]
    assert all(row["status"] == "completed" for row in pipeline["stages"])
    assert config["task_policy"]["sandbox"] == {
        "cpus": 4,
        "memory_gib": 8,
        "disk_gib": 10,
        "gpu": False,
    }
    folders = {
        name.removesuffix("/sandbox-claim.json")
        for name in snapshot.rows
        if name.endswith("/sandbox-claim.json")
    }
    verify_sdk_inventory(pipeline, folders)
    evidence, owners, claims, unrecorded = [], [], [], []

    def cleanup_row(name, value):
        assert value["passed"] and not value.get("remaining")
        assert not value.get("creation_uncertain")
        assert all(
            box["deleted"] and (box["cpu"], box["memory"], box["disk"]) == (4, 8, 10)
            for box in value["sandboxes"]
        )
        evidence.append(
            {
                "path": name,
                "sha256": snapshot.rows[name]["sha256"],
                "cleanup_verified": True,
                "sandboxes": value["sandboxes"],
            }
        )

    for folder in sorted(folders):
        stage = snapshot.read_json(folder + "/configuration.json")
        owner = stage["campaign"]
        assert owner.startswith(config["campaign"] + "-")
        claim = snapshot.read_json(folder + "/sandbox-claim.json")
        assert claim["owner"] == owner and claim["state"] == "created"
        assert claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
        owners.append(owner)
        claims.append(claim)
        name = folder + "/cleanup.json"
        cleanup_row(name, snapshot.read_json(name))

    native = snapshot.read_json("native/execution.json")
    assert native["task_resources"] == {"cpus": 4, "memory_mb": 8192, "storage_mb": 10240}
    paths = {
        name
        for name in snapshot.rows
        if name.startswith("native/") and name.endswith("/remote-job.json")
    }
    assert paths == {f"native/{agent}/remote-job.json" for agent in ("oracle", "nop", "terminus-2")}
    for name in sorted(paths):
        record = snapshot.read_json(name)
        owner = check_native_ownership(record)
        owners.append(owner)
        if not record["cleanup"]["sandboxes"]:
            unrecorded.append(owner)
        cleanup_row(name, record["cleanup"])
    assert len(owners) == len(set(owners)) == len(folders) + 3
    assert len({claim["id"] for claim in claims}) == len(claims)
    return evidence, owners, claims, unrecorded


def verify_absence(provider, query_type, evidence, owners, claims):
    verify_claim_ids_absent(provider, claims)
    checked = {claim["id"] for claim in claims}
    for row in evidence:
        for box in row["sandboxes"]:
            if box["id"] in checked:
                continue
            try:
                provider.get(box["id"], request_timeout=30)
            except Exception as error:
                if type(error).__name__ != "DaytonaNotFoundError":
                    raise
            else:
                raise RuntimeError("Original recorded sandbox remains")
            checked.add(box["id"])
    for owner in owners:
        assert not list(
            provider.list(query_type(labels={"repo2rlenv.job": owner}), request_timeout=30)
        ), "Owned sandbox remains"
    return checked


def main():
    from daytona import Daytona, ListSandboxesQuery

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    base, number = args.private_root, args.number
    archive, payload = base / f"archives/{number:03}", base / f"launch/{number:03}-payload"
    claim_path = base / f"launch/{number:03}-submission.json"
    claim_raw = claim_path.read_bytes()
    claim = json.loads(claim_raw)
    config_raw = (payload / "campaign-config.json").read_bytes()
    assert sha(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
    snapshot = verify_snapshot_archive(
        restored=archive / "snapshot-restored",
        transport=archive / "snapshot-transport",
        recovery=archive / "failure-archive-readback.json",
        claim=claim_path,
        bootstrap=payload / "bootstrap.py",
    )
    assert snapshot.read_json("pipeline.json")["factory_revision"] == claim["factory_revision"]
    observations = [
        json.loads(p.read_text())
        for p in (base / "launch/typed-observations").glob(f"{number:03}-*.json")
    ]
    terminal = max(observations, key=lambda row: row["observed_at"])
    assert terminal["terminal"] is True and terminal["claim_sha256"] == sha(claim_raw)
    assert terminal["state"] in {"SUCCEEDED", "FAILED", "KILLED", "WORKER_FAILED"}
    evidence, owners, claims, unrecorded = collect_cleanup(snapshot, json.loads(config_raw))
    if not os.environ.get("DAYTONA_API_KEY"):
        os.environ["DAYTONA_API_KEY"] = subprocess.run(
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
    checked = verify_absence(Daytona(), ListSandboxesQuery, evidence, owners, claims)
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "complete": True,
        "owners": owners,
        "sandboxes": [],
        "original_cleanup_evidence": evidence,
        "original_all_cleanup_passed": True,
        "fresh_original_ids_absent": True,
        "all_original_sdk_claim_ids_checked": True,
        "original_sdk_claims": claims,
        "native_unrecorded_id_owners": unrecorded,
        "native_undispatched_preflight_claims": [],
        "source_configuration_sha256": sha(config_raw),
        "source_archive_format": "quiescent-tar-v1",
        "source_snapshot_manifest_sha256": snapshot.evidence["member_manifest_sha256"],
        "source_transport_manifest_sha256": snapshot.evidence["transport_manifest_sha256"],
        "ordinary_autonomous_export_seal_reconstructed": False,
        "verification_helper_sha256": sha(Path(__file__).read_bytes()),
        "scope": "Original bounded-stage receipts plus fresh exact ID/owner absence, including the permitted comparison-repair sandbox. No unrecorded native ID, scientific acceptance or cost inferred.",
    }
    raw = (json.dumps(result, indent=2) + "\n").encode()
    folder = archive / "cleanup-observations"
    folder.mkdir(exist_ok=True)
    destination = folder / (sha(raw) + ".json")
    assert not destination.exists()
    destination.write_bytes(raw)
    current = archive / "fresh-provider-cleanup.json"
    if current.exists():
        previous = current.read_bytes()
        preserved = folder / (sha(previous) + ".json")
        if preserved.exists():
            assert preserved.read_bytes() == previous
        else:
            preserved.write_bytes(previous)
    current.write_bytes(raw)
    assert current.read_bytes() == raw
    print(
        json.dumps(
            {
                "campaign": number,
                "owners_verified_absent": len(owners),
                "recorded_ids_verified_absent": len(checked),
                "native_unrecorded_id_owners": len(unrecorded),
                "complete": True,
            }
        )
    )


if __name__ == "__main__":
    main()
