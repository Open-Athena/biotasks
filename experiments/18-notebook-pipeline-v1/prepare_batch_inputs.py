"""Repackage the initial panel's raw inputs for a shared factory version."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from biotasks.factory_inputs import assemble
from biotasks.prompts import load_prompt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    shared = {"protocol.json": args.protocol.read_bytes()}
    for stage, name in [
        ("prompt", "notebook-task-v1"),
        ("review-prompt", "notebook-review-v1"),
        ("repair-prompt", "notebook-repair-v1"),
    ]:
        shared[stage + ".md"] = load_prompt(name).encode()
    args.output_directory.mkdir(exist_ok=False)
    records = []
    for seed in json.loads(args.panel.read_text())["seeds"]:
        source = args.source_directory / (seed["id"] + "-input.zip")
        with zipfile.ZipFile(source) as z:
            selected = [
                name
                for name in z.namelist()
                if name
                in {
                    "seed.json",
                    "seed.txt",
                    "input-manifest.json",
                    "SOURCE-LICENSE",
                    "source-DESCRIPTION.txt",
                }
                or name.startswith("data/")
                or name.endswith(".tar.gz")
            ]
        result = assemble(source, selected, shared, args.output_directory / (seed["id"] + ".zip"))
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        records.append({"seed": seed["id"], "source_archive_sha256": digest.hexdigest(), **result})
    report = {
        "status": "prepared_not_submitted",
        "shared_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in shared.items()},
        "inputs": records,
    }
    (args.output_directory / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"prepared": len(records), "bytes": sum(r["size_bytes"] for r in records)}))


if __name__ == "__main__":
    main()
