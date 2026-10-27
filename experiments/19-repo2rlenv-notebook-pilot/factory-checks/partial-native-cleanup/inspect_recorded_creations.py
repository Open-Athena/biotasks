"""Read-only absence checks; preserve incomplete native dispatch claims as gaps.

Unlike the full regular-cleanup gate, this diagnostic permits an incomplete
native sequence. It cannot establish native qualification, release a reservation,
or certify that a claimed dispatch without its receipt did not happen.
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
sys.path.insert(0, str(EXPERIMENT / "panel-rounds/101"))
from verify_regular_cleanup import check_native_ownership  # noqa: E402


def main():
    from daytona import Daytona, ListSandboxesQuery

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    archive = args.private_root / f"archives/{args.number:03}"
    manifest_raw = (archive / "sealed-manifest.json").read_bytes()
    readback = json.loads((archive / "independent-readback.json").read_text())
    assert readback["all_files_download_verified"]
    assert readback["source_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest()
    entries = {row["path"]: row for row in json.loads(manifest_raw)["files"]}

    def original(name):
        raw = (archive / "files" / name).read_bytes()
        assert len(raw) == entries[name]["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entries[name]["sha256"]
        return json.loads(raw)

    owners, ids, native_outputs = set(), set(), set()
    for name in entries:
        if name.endswith("/sandbox-claim.json"):
            claim = original(name)
            assert claim["state"] == "created"
            assert claim["resources"] == {"cpu": 4, "memory": 8, "disk": 10}
            cleanup = original(name.removesuffix("sandbox-claim.json") + "cleanup.json")
            assert cleanup["passed"] and not cleanup["remaining"]
            assert not cleanup.get("creation_uncertain")
            owners.add(claim["owner"])
            ids.add(claim["id"])
        if name.startswith("native/") and name.endswith("/remote-job.json"):
            record = original(name)
            owners.add(check_native_ownership(record))
            native_outputs.add(name.removesuffix("/remote-job.json"))
            for box in record["cleanup"]["sandboxes"]:
                assert box["deleted"]
                ids.add(box["id"])
    gaps = []
    for name in entries:
        if name.startswith("native/trial-claims/") and name.endswith(".json"):
            claim = original(name)
            suffix = "native/" + Path(claim["output"]).name
            if suffix not in native_outputs:
                gaps.append(
                    {"path": name, "trial_id": claim["trial_id"], "solving": claim["solving"]}
                )

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
    for sandbox_id in sorted(ids):
        try:
            provider.get(sandbox_id, request_timeout=30)
        except Exception as error:
            if type(error).__name__ != "DaytonaNotFoundError":
                raise
        else:
            raise RuntimeError("Recorded sandbox remains")
    for owner in sorted(owners):
        assert not list(
            provider.list(
                ListSandboxesQuery(labels={"repo2rlenv.job": owner}),
                request_timeout=30,
            )
        ), "Recorded owner still has a sandbox"
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": args.number,
        "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "recorded_creation_ids_absent": sorted(ids),
        "recorded_owners_absent": sorted(owners),
        "native_dispatch_claims_without_receipt": gaps,
        "complete_for_recorded_creations": True,
        "all_dispatch_claims_resolved": not gaps,
        "fully_qualified_task": False,
        "accounting_reservation_released": False,
        "new_jobs": 0,
        "new_model_calls": 0,
        "resources_created_or_modified": False,
    }
    raw = (json.dumps(result, indent=2) + "\n").encode()
    destination = archive / "recorded-creation-cleanup"
    destination.mkdir(exist_ok=True)
    (destination / (hashlib.sha256(raw).hexdigest() + ".json")).write_bytes(raw)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
