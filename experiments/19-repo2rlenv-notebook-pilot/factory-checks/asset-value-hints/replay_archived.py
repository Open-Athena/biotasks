"""Replay discovery on a completely verified archive; no model or scientific run."""

import argparse
import asyncio
import hashlib
import json
import tarfile
import time
import zipfile
from pathlib import Path

from asset_value_hints import build_hints
from package_inspection import PackageInspection
from reference_inspection import ReferenceInspection

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert not args.output.exists(), "Retain previous replay observations separately"
raw_manifest = (args.archive / "sealed-manifest.json").read_bytes()
manifest = {r["path"]: r for r in json.loads(raw_manifest)["files"]}
receipt = json.loads((args.archive / "independent-readback.json").read_text())
assert receipt["all_files_download_verified"]
assert receipt["source_manifest_sha256"] == hashlib.sha256(raw_manifest).hexdigest()
root = args.archive / "files"
checked = {}


def original(name):
    raw = (root / name).read_bytes()
    row = manifest[name]
    assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    checked[name] = row["sha256"]
    return json.loads(raw)


catalog = original("grading/review-inspection/package-sources/catalog.json")["packages"]
summary = original("reference/trial/dependency-assets-summary.json")
removed = original("reference/trial/dependency-exclusions-applied.json")
candidate = original("materialization/candidate.json")
output_root = root / "materialization/reference"
outputs = {}
for name in candidate["output_paths"]:
    row = manifest["materialization/reference/" + name]
    outputs[name] = {k: row[k] for k in ("sha256", "bytes")}
deadline = time.time() + 300


class RecordedPackages:
    members = staticmethod(PackageInspection.members)
    open_member = staticmethod(PackageInspection.open_member)

    def remaining(self):
        if time.time() >= deadline:
            raise TimeoutError("Read-only replay allowance exhausted")

    async def archive(self, package):
        self.remaining()
        record = catalog.get(package) or {}
        spec = record.get("distribution")
        if not spec:
            raise ValueError("Original locked source is unavailable")
        digest = spec["hash"].removeprefix("sha256:")
        names = [
            n
            for n, row in manifest.items()
            if Path(n).name.startswith(digest + ".")
            and row["sha256"] == digest
            and row["bytes"] == spec["size"]
        ]
        if not names:
            raise ValueError("Original archive did not retain this package source")
        name = sorted(names)[0]
        path = root / name
        assert path.stat().st_size == spec["size"]
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
        checked[name] = digest
        return zipfile.ZipFile(path) if record["kind"] == "universal_wheel" else tarfile.open(path)


started = time.time()
result = asyncio.run(
    build_hints(
        RecordedPackages(),
        ReferenceInspection(output_root, outputs, deadline),
        summary["priority_matches"],
        removed["files"] if removed["excluded_files_absent"] else [],
    )
)
args.output.write_text(
    json.dumps(
        {
            "source_archive_manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
            "original_metadata_and_source_sha256": checked,
            "seconds": round(time.time() - started, 3),
            "hints": result,
            "scope": "Read-only replay of original recorded package sources and final outputs. No model, scientific recomputation, task edit or provider resource.",
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {
            "source_archive_manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
            "candidates": len(result["candidates"]),
            "source_files_inspected": sum(
                r["status"] == "installed_source_literals_inspected" for r in result["candidates"]
            ),
            "findings": len(result["findings"]),
            "output_files_inspected": sum(
                r["status"] == "numeric_cells_inspected" for r in result["reference_coverage"]
            ),
            "seconds": round(time.time() - started, 3),
        }
    )
)
