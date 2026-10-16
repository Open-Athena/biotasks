"""Read-only recovery of bounded pilot diagnostics through an Iris job log.

No model calls, task generation, sandbox creation or cloud mutations occur here.
Original evidence stays at its existing private artifact destination.
"""

import base64
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor

import fsspec

SELECTED = {
    "bootstrap-status.json",
    "campaign.log",
    "setup.log",
    "reference-export.log",
    "inputs.json",
    "pilot/started.json",
    "pilot/compatibility.json",
    "pilot/escaping-compatibility.json",
    "pilot/requests.sqlite",
    "pilot/daytona-budget.sqlite3",
    "pilot/infrastructure-preflight.json",
    "pilot/infrastructure-preflight-claim.json",
    "pilot/generation-summary.json",
    "pilot/quality-result.json",
    "pilot/outcome.json",
}


def priority(entry):
    name = entry["path"]
    if name.startswith(("grading/", "native/")) and name.rsplit("/", 1)[-1] in {
        "materialization-candidate.json",
        "manifest.json",
        "independent-solution.json",
        "independent-result.json",
        "final-candidate.json",
        "final-controls.json",
        "instruction.md",
        "grade.py",
        "probes.json",
        "review.json",
        "review-repair.json",
        "result.json",
        "configuration.json",
        "requests.sqlite",
        "system-prompt.md",
        "isolation.json",
    }:
        return (0, name)
    if name.startswith("specification/") and name.rsplit("/", 1)[-1] in {
        "specification.json",
        "review.md",
        "task-brief.md",
        "validation-plan.md",
        "validation-handoff.md",
        "result.json",
        "configuration.json",
        "requests.sqlite",
        "catalog.json",
        "artifact.json",
        "operation.json",
    }:
        return (0, name)
    if name in SELECTED or name.startswith("pilot/trial-claims/"):
        return (0, name)
    if name.endswith(("/remote-job.json", "/trial.json", "/result.json")):
        return (1, name)
    if name.startswith(("pilot/fidelity/", "pilot/quality/revisions/", "pilot/tasks/")):
        return (2, name)
    return (3, name)


def main():
    prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
    with fsspec.open(prefix + "/export-manifest.json", "rb").open() as stream:
        manifest_bytes = stream.read(512_001)
    if len(manifest_bytes) > 512_000:
        raise ValueError("Manifest exceeds the recovery transport limit")
    manifest = json.loads(manifest_bytes)
    total = 0
    skipped = []
    selected_entries = []
    print("RECOVERY_MANIFEST " + base64.b64encode(manifest_bytes).decode(), flush=True)
    for entry in sorted(manifest["files"], key=priority):
        relative = entry["path"]
        selected = (
            relative in SELECTED
            or (relative.startswith("pilot/trial-claims/") and relative.endswith(".json"))
            or (relative.startswith(("pilot/tasks/", "pilot/fidelity/")))
            or (relative.startswith("pilot/campaign/") and relative.endswith(".json"))
            or relative.startswith("pilot/quality/revisions/")
            or (relative.startswith("pilot/quality/") and relative.endswith("/task.tar.gz"))
            or (relative.startswith("pilot/quality/") and relative.endswith(".json"))
            or relative.startswith("pilot/quality/trials/")
            or relative.startswith("trials/")
            or relative.startswith("continuation/")
            or (relative.startswith("reference/") and "/outputs/" not in relative)
            or relative.startswith("coverage/")
            or relative.startswith(("grading/", "grading-retrieval/", "native/"))
            or (relative.startswith("reference-replay/") and "/outputs/" not in relative)
            or (relative.startswith("reference-setup/") and "/outputs/" not in relative)
            or relative.startswith(("preparation/", "schema-probe/", "specification/"))
        )
        if not selected:
            continue
        if relative.startswith("specification/package-sources/") and not relative.endswith(".json"):
            # Verified distributions are retained in the full archive. Do not
            # crowd final text and tool traces out of the diagnostic log transfer.
            continue
        # Preparation responses can exceed the old per-file diagnostic bound.
        # Keep the total log-transfer bound; full evidence remains in storage.
        if (
            entry["bytes"] > 256_000
            and not relative.startswith(("preparation/", "schema-probe/", "specification/"))
        ) or total + entry["bytes"] > 4_000_000:
            skipped.append(relative)
            print("RECOVERY_SKIPPED " + json.dumps(entry), flush=True)
            continue
        selected_entries.append(entry)
        total += entry["bytes"]

    def fetch(entry):
        with fsspec.open(prefix + "/" + entry["path"], "rb").open() as stream:
            data = stream.read(entry["bytes"] + 1)
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Recovered diagnostic failed its original export hash")
        return entry, data

    with ThreadPoolExecutor(max_workers=4) as pool:
        for entry, data in pool.map(fetch, selected_entries):
            emit_chunks(entry, data)
    print("RECOVERY_COMPLETE " + json.dumps({"bytes": total, "skipped": skipped}), flush=True)


def emit_chunks(entry, data):
    relative = entry["path"]
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


if __name__ == "__main__":
    main()
