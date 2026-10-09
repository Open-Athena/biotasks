"""Recover oversized Pi text from the already preserved private run archive.

No model call, task execution, sandbox creation or mutation of source artifacts.
The source location is supplied only through the private runtime environment.
"""

import base64
import gzip
import hashlib
import json
import os

import fsspec

prefix = os.environ["BIOTASKS_RECOVERY_PREFIX"].rstrip("/")
with fsspec.open(prefix + "/manifest.json", "rt").open() as source:
    manifest = json.load(source)
entries = [row for row in manifest if row["path"].endswith("/agent/pi.txt")]
if len(entries) != 1:
    raise ValueError("Expected exactly one preserved Pi trajectory")
entry = entries[0]
if entry["size"] > 32 * 1024**2:
    raise ValueError("Trajectory exceeds bounded recovery size")
with fsspec.open(prefix + "/records/" + entry["path"], "rb").open() as source:
    value = source.read(entry["size"] + 1)
if len(value) != entry["size"] or hashlib.sha256(value).hexdigest() != entry["sha256"]:
    raise ValueError("Preserved trajectory does not match its durable manifest")
artifacts = {
    "agent/pi.txt": value.decode(),
    "recovery.json": json.dumps(
        {"source_entry": entry, "readback_verified": True, "source_mutated": False}
    ),
}
packed = gzip.compress(json.dumps(artifacts).encode())
encoded = base64.b64encode(packed).decode()
chunks = [encoded[i : i + 6000] for i in range(0, len(encoded), 6000)]
print(
    "BIOTASKS_SMOKE_ARCHIVE "
    + json.dumps({"chunks": len(chunks), "sha256": hashlib.sha256(packed).hexdigest()}),
    flush=True,
)
for index, chunk in enumerate(chunks):
    print(f"BIOTASKS_SMOKE_CHUNK {index} {chunk}", flush=True)
print("BIOTASKS_RECOVERY_COMPLETE " + json.dumps({"bytes": len(value)}), flush=True)
