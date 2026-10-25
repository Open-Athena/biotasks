"""Convert every hash-pinned development source; never execute notebook code."""

import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from biotasks.notebook_script import UnsupportedNotebook, export_python

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--private-root", type=Path, required=True)
parser.add_argument("--inputs", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists()
args.output.mkdir()
rows = []
for source in json.loads(args.inputs.read_text())["records"]:
    prior = source["original_asset_campaign"]
    payload = args.private_root / f"launch/{prior:03}-payload"
    config_raw = (payload / "campaign-config.json").read_bytes()
    manifest = json.loads((payload / "inputs.json").read_text())
    assert hashlib.sha256(config_raw).hexdigest() == manifest["files"]["campaign-config.json"]
    with (payload / "biotasks.tar").open("rb") as stream:
        assert (
            hashlib.file_digest(stream, "sha256").hexdigest() == manifest["files"]["biotasks.tar"]
        )
    asset = source["source_assets"]["notebook_file"]
    with tarfile.open(payload / "biotasks.tar") as archive:
        raw = archive.extractfile(asset["path"]).read()
    assert len(raw) == asset["bytes"] and hashlib.sha256(raw).hexdigest() == asset["sha256"]
    result = {
        "source_id": source["source_id"],
        "source_url": source["source_url"],
        "source_sha256": asset["sha256"],
        "source_payload_campaign": prior,
    }
    with tempfile.TemporaryDirectory(prefix="biotasks19-conversion-check-") as temporary:
        path = Path(temporary) / "source.ipynb"
        path.write_bytes(raw)
        try:
            script, receipt = export_python(path)
        except UnsupportedNotebook as error:
            result.update(status="unsupported_conversion_profile", reason=str(error))
        else:
            assert export_python(path) == (script, receipt)
            assert receipt["ordered_code_equivalence"] and not receipt["executed"]
            assert receipt["source_sha256"] == asset["sha256"]
            assert receipt["code_cells"] == source["original_code_cells"]
            name = f"{len(rows) + 1:02}-{asset['sha256'][:12]}.receipt.json"
            (args.output / name).write_text(json.dumps(receipt, indent=2) + "\n")
            result.update(status="converted", receipt=name, script_bytes=len(script.encode()))
    rows.append(result)
summary = {
    "converter_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_count": len(rows),
    "converted_count": sum(r["status"] == "converted" for r in rows),
    "results": rows,
    "new_jobs_models_sandboxes": 0,
    "scientific_execution": False,
    "scope": "Current converter determinism and recorded ordered-code equivalence on original inputs only; not dependency setup, reference execution, scientific validation or publication.",
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "results"}))
