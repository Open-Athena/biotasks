"""Read existing native stage exports; never create jobs, call models, or mutate sandboxes."""

import base64
import hashlib
import json
from pathlib import Path

import fsspec

NAMES = {
    "outcome.json",
    "suite.json",
    "result.json",
    "cleanup.json",
    "owned-sandboxes.jsonl",
    "sandbox-resources.jsonl",
    "network-preflights.jsonl",
    "cleanup-log.txt",
    "native-summary.json",
    "summary.json",
    "preflight.json",
}
files = {}
observations = []
total = 0


def read(uri, bound=256_000):
    with fsspec.open(uri, "rb").open() as stream:
        data = stream.read(bound + 1)
    if len(data) > bound:
        raise ValueError("Evidence file exceeds bounded recovery size")
    return data


def keep(name, data, expected=None):
    global total
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Unsafe evidence path")
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("Original native export hash mismatch")
    total += len(data)
    if total > 8_000_000:
        raise ValueError("Bounded recovery capacity exceeded")
    files[name] = (data, digest)


for plan in json.loads(Path("recovery-plan.json").read_text()):
    seed, prefix = plan["seed"], plan["prefix"].rstrip("/")
    for slot in plan["native_slots"]:
        base = prefix + "/" + slot
        record = {"seed": seed, "slot": slot, "recovered": [], "missing_manifest": False}
        try:
            manifest_bytes = read(base + "/manifest.json", 1_000_000)
        except FileNotFoundError:
            record["missing_manifest"] = True
            observations.append(record)
            continue
        keep(seed + "/" + slot + "/manifest.json", manifest_bytes)
        for item in json.loads(manifest_bytes):
            relative = item["path"]
            if Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise ValueError("Unsafe path in original native manifest")
            if Path(relative).name not in NAMES:
                continue
            if item["size"] > 256_000:
                record.setdefault("skipped_oversized", []).append(relative)
                continue
            data = read(base + "/records/" + relative)
            if len(data) != item["size"]:
                raise ValueError("Native evidence length differs from original manifest")
            keep(seed + "/" + slot + "/records/" + relative, data, item["sha256"])
            record["recovered"].append(relative)
        try:
            cleanup = read(base + "/cleanup.json")
        except FileNotFoundError:
            record["post_export_cleanup_present"] = False
        else:
            keep(seed + "/" + slot + "/post-export-cleanup.json", cleanup)
            record["post_export_cleanup_present"] = True
        observations.append(record)
keep("native-recovery-observations.json", json.dumps(observations, indent=2).encode())
manifest = {
    "files": [
        {"path": name, "sha256": value[1], "bytes": len(value[0])} for name, value in files.items()
    ]
}
print("RECOVERY_MANIFEST " + base64.b64encode(json.dumps(manifest).encode()).decode(), flush=True)
for name, (data, digest) in files.items():
    encoded = base64.b64encode(data).decode()
    for offset in range(0, len(encoded), 6000):
        print(
            "RECOVERY_CHUNK "
            + json.dumps(
                {
                    "path": name,
                    "offset": offset,
                    "data": encoded[offset : offset + 6000],
                    "sha256": digest,
                }
            ),
            flush=True,
        )
print("RECOVERY_COMPLETE " + json.dumps({"bytes": total, "skipped": []}), flush=True)
