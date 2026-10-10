"""Read-only recovery of bounded pilot diagnostics through an Iris job log.

No model calls, task generation, sandbox creation or cloud mutations occur here.
Original evidence stays at its existing private artifact destination.
"""

import base64
import hashlib
import json
import os

import fsspec

SELECTED = {
    "bootstrap-status.json",
    "campaign.log",
    "setup.log",
    "inputs.json",
    "pilot/started.json",
    "pilot/compatibility.json",
    "pilot/requests.sqlite",
    "pilot/daytona-budget.sqlite3",
    "pilot/infrastructure-preflight.json",
    "pilot/infrastructure-preflight-claim.json",
    "pilot/generation-summary.json",
    "pilot/quality-result.json",
    "pilot/outcome.json",
}


def main():
    prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
    with fsspec.open(prefix + "/export-manifest.json", "rb").open() as stream:
        manifest_bytes = stream.read(512_001)
    if len(manifest_bytes) > 512_000:
        raise ValueError("Manifest exceeds the recovery transport limit")
    manifest = json.loads(manifest_bytes)
    total = 0
    skipped = []
    print("RECOVERY_MANIFEST " + base64.b64encode(manifest_bytes).decode(), flush=True)
    for entry in manifest["files"]:
        relative = entry["path"]
        selected = (
            relative in SELECTED
            or (relative.startswith("pilot/trial-claims/") and relative.endswith(".json"))
            or (relative.startswith(("pilot/tasks/", "pilot/fidelity/")))
            or (relative.startswith("pilot/campaign/") and relative.endswith(".json"))
            or relative.startswith("pilot/quality/revisions/")
            or (relative.startswith("pilot/quality/") and relative.endswith("/task.tar.gz"))
            or (relative.startswith("pilot/quality/") and relative.endswith(".json"))
        )
        if not selected:
            continue
        if entry["bytes"] > 256_000 or total + entry["bytes"] > 1_000_000:
            skipped.append(relative)
            print("RECOVERY_SKIPPED " + json.dumps(entry), flush=True)
            continue
        with fsspec.open(prefix + "/" + relative, "rb").open() as stream:
            data = stream.read(entry["bytes"] + 1)
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Recovered diagnostic failed its original export hash")
        total += len(data)
        encoded = base64.b64encode(data).decode()
        # Bound individual log lines; reassembly is checked against the original hash.
        for offset in range(0, len(encoded), 6000):
            print(
                "RECOVERY_CHUNK "
                + json.dumps(
                    {
                        "path": relative,
                        "offset": offset,
                        "data": encoded[offset : offset + 6000],
                        "sha256": entry["sha256"],
                    }
                ),
                flush=True,
            )
    print("RECOVERY_COMPLETE " + json.dumps({"bytes": total, "skipped": skipped}), flush=True)


if __name__ == "__main__":
    main()
