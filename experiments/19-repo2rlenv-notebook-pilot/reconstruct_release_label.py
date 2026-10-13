"""Check upstream labels from a separate, reconstructed evidence copy."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.quality.labels import label_from_quality, write_labeled_copy
from repo2rlenv.quality.loop.artifacts import parse_task, probe_variant
from repo2rlenv.quality.loop.models import SemanticProbe

source = Path(sys.argv[1]).resolve()
dest = Path(sys.argv[2]).resolve()
if dest.exists():
    raise FileExistsError(dest)
shutil.copytree(source, dest)
original = source / "pilot/quality/result.json"
q = json.loads(original.read_text())


def local(p):
    assert p.startswith("/evidence/")
    return dest / p.removeprefix("/evidence/")


task = local(q["task_path"])
q["task_path"] = str(task)
assert inspect_bundle(task)["bundle_hash"] == q["bundle_hash"]
for t in q["trials"]:
    raw = local(t["result"])
    t["result"] = str(raw)
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == t["result_sha256"]
    if t["role"] == "probe":
        d = json.loads(raw.read_text())
        variant = (
            raw.parents[4] / "probes" / raw.parents[2].name / Path(d["config"]["task"]["path"]).name
        )
        if variant.exists():
            shutil.rmtree(variant)  # Only the disposable evidence copy.
        probe_variant(task, SemanticProbe.model_validate(t["probe"]), variant)
        assert inspect_bundle(variant)["bundle_hash"] == t["bundle_hash"]
        assert parse_task(variant).checksum == d["task_checksum"]
result = dest / "quality-local-paths.json"
result.write_text(json.dumps(q, indent=2))
label = label_from_quality(task, result)
assert label.status == "verified"
labeled = dest / "labeled" / task.name
write_labeled_copy(task, labeled, label)
assert inspect_bundle(labeled)["bundle_hash"] == q["bundle_hash"]
receipt = {
    "original_quality_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
    "derived_quality_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
    "bundle_hash": q["bundle_hash"],
    "labeled_task": str(labeled),
    "label_status": label.status,
    "changes": "Local evidence paths and deterministic upstream probe reconstruction only; raw trial bytes unchanged.",
}
(dest / "derivation.json").write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt))
