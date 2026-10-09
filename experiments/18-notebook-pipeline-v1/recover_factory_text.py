"""Read bounded factory evidence from durable storage; never run or edit a task.

Private recovery-plan.json supplies seed identities and artifact prefixes. The
output is a checksummed text archive for the existing local log decoder. Large
and binary artifacts remain at their original locations and are listed as omitted.
"""

import base64
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath

import fsspec

MAX_FILE = 4 * 1024**2
MAX_TOTAL = 24 * 1024**2


def collect(plan, read):
    artifacts, inventory, omissions = {}, [], []
    deferred = []
    used = 0

    def add(name, uri, expected=None):
        nonlocal used
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError("Unsafe evidence path")
        if name in artifacts:
            raise ValueError("Duplicate evidence path")
        if expected and expected["size"] > MAX_FILE:
            omissions.append({"path": name, "reason": "file_size_bound", "source_entry": expected})
            return
        try:
            value = read(uri, MAX_FILE + 1)
        except FileNotFoundError:
            omissions.append({"path": name, "reason": "not_available"})
            return
        digest = hashlib.sha256(value).hexdigest()
        if expected and (len(value) != expected["size"] or digest != expected["sha256"]):
            raise ValueError("Durable evidence differs from its source manifest")
        if len(value) > MAX_FILE or used + len(value) > MAX_TOTAL:
            omissions.append({"path": name, "reason": "recovery_size_bound"})
            return
        try:
            text = value.decode("utf-8")
        except UnicodeError:
            omissions.append({"path": name, "reason": "binary"})
            return
        artifacts[name] = text
        used += len(value)
        inventory.append({"path": name, "size": len(value), "sha256": digest,
                          "source_manifest_verified": expected is not None})
        return text

    for item in plan:
        seed, prefix = item["seed"], item["prefix"].rstrip("/")
        raw = add(seed + "/pipeline-summary.json", prefix + "/pipeline-summary.json")
        if raw is None:
            continue
        summary = json.loads(raw)
        if summary["seed"] != seed:
            raise ValueError("Recovery seed identity mismatch")
        if summary["status"] == "accepted":
            add(seed + "/acceptance.json", prefix + "/acceptance.json")
        for stage in summary["stages"]:
            slot = stage["slot"]
            destination = seed + "/" + slot + "/"
            origin = prefix + "/" + slot
            if slot in {"specification", "construction", "review", "repair", "review_after_repair"}:
                for name in ("result.json", "artifact-manifest.json", "final-task-manifest.json",
                             "deleted-inputs.json", "zcode-stderr.txt"):
                    add(destination + "records/" + name, origin + "/records/" + name)
                deferred.append((destination + "records/zcode-events.jsonl",
                                 origin + "/records/zcode-events.jsonl", None))
                add(destination + "run-spec.json", origin + "/run-spec.json")
                manifest = artifacts.get(destination + "records/artifact-manifest.json")
                if manifest:
                    for entry in json.loads(manifest):
                        # Large inputs stay in durable storage. Recover authored text,
                        # including rejection, proposal, audit and scientific code.
                        name = entry["path"]
                        if PurePosixPath(name).suffix in {".json", ".md", ".py", ".sh", ".toml", ".R", ".yaml", ".yml"} or PurePosixPath(name).name == "Dockerfile":
                            add(destination + "workspace/" + name, origin + "/workspace/" + name, entry)
                        else:
                            omissions.append({"path": destination + "workspace/" + name,
                                              "reason": "outside_text_selection", "source_entry": entry})
            else:
                manifest = add(destination + "manifest.json", origin + "/manifest.json")
                if manifest:
                    for entry in json.loads(manifest):
                        name = entry["path"]
                        args = (destination + "records/" + name, origin + "/records/" + name, entry)
                        if PurePosixPath(name).suffix in {".log", ".txt", ".jsonl"}:
                            deferred.append(args)
                        else:
                            add(*args)
            deferred.append((destination + "launcher.log", origin + "/launcher.log", None))
    # Preserve every seed's small decision records before spending the bounded
    # text allowance on verbose traces. Omitted traces remain in durable storage.
    for args in deferred:
        add(*args)
    artifacts["recovery.json"] = json.dumps({"files": inventory, "omissions": omissions,
        "source_mutated": False, "complete_binary_artifact_recovery": False}, indent=2)
    return artifacts


def main():
    def read(uri, size):
        with fsspec.open(uri, "rb").open() as source:
            return source.read(size)

    result = collect(json.loads(Path("recovery-plan.json").read_text()), read)
    raw = json.dumps(result).encode()
    if len(raw) > 32 * 1024**2:
        raise ValueError("Recovery exceeds local decoder bound")
    packed = gzip.compress(raw)
    if len(packed) > 5 * 1024**2:
        raise ValueError("Recovery exceeds bounded log transport")
    encoded = base64.b64encode(packed).decode()
    chunks = [encoded[i:i + 6000] for i in range(0, len(encoded), 6000)]
    print("BIOTASKS_SMOKE_ARCHIVE " + json.dumps({"chunks": len(chunks),
        "sha256": hashlib.sha256(packed).hexdigest()}), flush=True)
    for index, chunk in enumerate(chunks):
        print(f"BIOTASKS_SMOKE_CHUNK {index} {chunk}", flush=True)


if __name__ == "__main__":
    main()
