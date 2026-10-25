"""Check original ten-source inputs against the live common policy; never launch."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--private-root", type=Path, required=True)
parser.add_argument("--panel", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists()
launch = args.private_root / "launch"
canonical = json.loads((launch / "158-payload/campaign-config.json").read_text())
source_keys = {"campaign", "notebook_file", "seed_file", "source_notices_file"}
policy = {k: v for k, v in canonical.items() if k not in source_keys}
records = []
for original in json.loads(args.panel.read_text())["records"]:
    prior = original["campaign"]
    active = (
        158
        if original["source_id"] == "mdanalysis-rmsd"
        else (159 if original["source_id"] == "matchms-spectral-matching" else None)
    )
    number = active or prior
    payload = launch / f"{number}-payload"
    raw_config = (payload / "campaign-config.json").read_bytes()
    config = json.loads(raw_config)
    assert {k: v for k, v in config.items() if k not in source_keys} == policy
    manifest = json.loads((payload / "inputs.json").read_text())
    assert hashlib.sha256(raw_config).hexdigest() == manifest["files"]["campaign-config.json"]
    with (payload / "biotasks.tar").open("rb") as stream:
        assert (
            hashlib.file_digest(stream, "sha256").hexdigest() == manifest["files"]["biotasks.tar"]
        )
    assets = {}
    with tarfile.open(payload / "biotasks.tar") as archive:
        for key in ("notebook_file", "seed_file", "source_notices_file"):
            if key not in config:
                continue
            name = "experiments/19-repo2rlenv-notebook-pilot/" + config[key]
            raw = archive.extractfile(name).read()
            assets[key] = {
                "path": name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
            if key == "seed_file":
                seed = json.loads(raw)
                assert len(seed) == 1 and "question_text" not in seed[0]
                seed = seed[0]
            elif key == "notebook_file":
                notebook = json.loads(raw)
                language = notebook.get("metadata", {}).get("language_info", {}).get("name")
                code_cells = sum(cell["cell_type"] == "code" for cell in notebook["cells"])
                del notebook
    assert seed["source_sha256"] == assets["notebook_file"]["sha256"]
    records.append(
        {
            "domain": original["domain"],
            "source_id": original["source_id"],
            "source_url": seed["url"],
            "source_revision": seed["source_revision"],
            "original_asset_campaign": number,
            "source_assets": assets,
            "recorded_notebook_language": language,
            "original_code_cells": code_cells,
            "source_policy_equals_active_common_policy": True,
            "seed_fields": sorted(seed),
            "active_fresh_campaign": active,
            "status": "live_validation_pending"
            if active
            else "source_inputs_inspected_not_funded_or_launched",
        }
    )
assert len(records) == 10 and len({r["domain"] for r in records}) == 10
args.output.write_text(
    json.dumps(
        {
            "runtime_revision": "b69ae30f5dc74b0b7ac88c4f72cb4410a5e59a46",
            "common_policy_sha256": hashlib.sha256(
                json.dumps(policy, sort_keys=True).encode()
            ).hexdigest(),
            "source_count": len(records),
            "records": records,
            "new_jobs_models_sandboxes": 0,
            "scope": "Original payload/source identity and policy compatibility only. The eight remaining sources are not funded, frozen on the current runtime or launched by this check. Not an execution/qualification result. R remains deferred.",
        },
        indent=2,
    )
    + "\n"
)
print(
    "All ten original notebook identities match their seed records and the active common execution policy; only158/159are live."
)
