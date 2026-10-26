"""Execute worker-generated derivations and an oracle with private answers hidden."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from grading_remote import AUTHOR, ORACLE, hashes, owned, run_as

PRIVATE = Path("/work/grading-private")


def verify_sources(manifest):
    import hashlib

    for item in manifest["files"]:
        path = Path(item["local_path"])
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Original input identity changed")


def inventory(root):
    return [
        dict(path=name, sha256=digest, bytes=(root / name).stat().st_size)
        for name, digest in hashes(root).items()
    ]


def main():
    candidate = json.loads((PRIVATE / "materialization.json").read_text())
    inspection = Path("/work/construction-inspection")
    inspection.mkdir(exist_ok=True)
    os.chown(inspection, 0, AUTHOR)
    inspection.chmod(0o750)
    # These fields are supplied by the trusted controller after checking the
    # worker's observation-bound declaration, never chosen from filenames here.
    receipt_path = PRIVATE / "final-environment-removals.json"
    subprocess.run(
        [
            "/work/venv/bin/python",
            "/work/dependency_assets.py",
            "finalize",
            str(PRIVATE / "materialization.json"),
            str(receipt_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    excluded = candidate["effective_dependency_exclusions"]
    receipt = json.loads(receipt_path.read_text())
    sources = json.loads(Path("/work/original-inputs.json").read_text())
    verify_sources(sources)
    original = hashes(Path("/work/reference"))
    for item in sources["files"]:
        Path(item["local_path"]).chmod(0o444)
    work = Path("/work/author/derive-case")
    shutil.rmtree(work, ignore_errors=True)
    owned(work, AUTHOR, 0o700)
    code = work / "derive.py"
    code.write_text(candidate["derive_code"])
    code.chmod(0o444)
    destination = work / "bundle"
    execution = run_as(
        AUTHOR,
        [
            "/work/venv/bin/python",
            str(code),
            "--source-inputs",
            "/work/original-inputs.json",
            "--reference-dir",
            "/work/reference",
            "--destination",
            str(destination),
        ],
        work,
        candidate["seconds"],
    )
    result = {
        "status": "incomplete",
        "derivation": execution,
        "environment_removal_receipt": receipt,
    }
    try:
        verify_sources(sources)
        if hashes(Path("/work/reference")) != original:
            raise ValueError("Original reference changed")
        if execution["exit_code"] != 0:
            return result
        actual = hashes(destination)
        expected = {"inputs/" + p for p in candidate["input_paths"]} | {
            "reference/" + p for p in candidate["output_paths"]
        }
        if set(actual) != expected:
            raise ValueError(
                "Derived artifact inventory differs from declaration: "
                + json.dumps(
                    {
                        "missing": sorted(expected - set(actual)),
                        "unexpected": sorted(set(actual) - expected),
                    }
                )
            )
        # Freeze and archive derivation products before exposing only inputs.
        saved = PRIVATE / "materialized"
        shutil.rmtree(saved, ignore_errors=True)
        shutil.copytree(destination, saved)
        result["inputs"] = inventory(saved / "inputs")
        result["reference"] = inventory(saved / "reference")
        task = Path("/task")
        shutil.rmtree(task, ignore_errors=True)
        task.mkdir(mode=0o755)
        shutil.copytree(saved / "inputs", task / "inputs")
        for p in [task / "inputs", *(task / "inputs").rglob("*")]:
            p.chmod(0o555 if p.is_dir() else 0o444)
        (task / "oracle.py").write_text(candidate["oracle_code"])
        (task / "oracle.py").chmod(0o444)
        owned(task / "outputs", ORACLE, 0o700)
        # A private writable home supports ordinary library caches without
        # polluting the declared output inventory or making inputs mutable.
        owned(task / "home", ORACLE, 0o700)
        reference = Path("/work/reference")
        reference.chmod(0o700)
        for item in sources["files"]:
            Path(item["local_path"]).chmod(0o000)
        try:
            isolation = run_as(
                ORACLE,
                [
                    "/work/venv/bin/python",
                    "-c",
                    "from pathlib import Path\n"
                    "for p in ['/work/reference', '/work/author', '/work/grading-private', '/work/construction-inspection']:\n"
                    " try:\n  list(Path(p).iterdir())\n"
                    " except PermissionError:\n  continue\n"
                    " raise RuntimeError('Private reference accessible')\n"
                    "print('isolated')",
                ],
                task,
                15,
            )
            result["oracle_isolation"] = isolation
            if isolation["exit_code"] != 0:
                raise ValueError("Oracle isolation failed")
            result["oracle"] = run_as(
                ORACLE,
                [
                    "/work/venv/bin/python",
                    "/task/oracle.py",
                    "--input-dir",
                    "/task/inputs",
                    "--output-dir",
                    "/task/outputs",
                ],
                task / "home",
                candidate["seconds"],
            )
        finally:
            reference.chmod(0o555)
            for item in sources["files"]:
                Path(item["local_path"]).chmod(0o444)
        if result["oracle"]["exit_code"] != 0:
            return result
        result["oracle_outputs"] = inventory(task / "outputs")
        if {p["path"] for p in result["oracle_outputs"]} != set(candidate["output_paths"]):
            raise ValueError("Oracle artifact inventory differs from declaration")
        if hashes(task / "inputs") != {p["path"]: p["sha256"] for p in result["inputs"]}:
            raise ValueError("Oracle modified supplied inputs")
        subprocess.run(
            [
                "/work/venv/bin/python",
                "/work/dependency_assets.py",
                "verify-absence",
                str(PRIVATE / "materialization.json"),
                str(receipt_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        catalog = PRIVATE / "dependency-assets-final.json"
        outputs_path = PRIVATE / "final-outputs.json"
        outputs_path.write_text(json.dumps(result["reference"]))
        source_path = PRIVATE / "original-source.py"
        source_path.write_text(candidate["original_source"])
        subprocess.run(
            [
                "/work/venv/bin/python",
                "/work/dependency_assets.py",
                "inspect",
                str(outputs_path),
                str(catalog),
                str(source_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assets = json.loads(catalog.read_text())
        visible_catalog = inspection / "dependency-assets-final.json"
        visible_catalog.write_bytes(catalog.read_bytes())
        os.chown(visible_catalog, 0, AUTHOR)
        visible_catalog.chmod(0o440)
        result["environment"] = {
            "exclusions": excluded,
            "removal_receipt": json.loads(receipt_path.read_text()),
            "asset_catalog": {
                "bytes": catalog.stat().st_size,
                "sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            },
            "asset_summary": assets["summary"],
        }
        result["status"] = "executed_requires_scientific_validation"
        return result
    finally:
        verify_sources(sources)
        if hashes(Path("/work/reference")) != original:
            raise ValueError("Original reference changed")


if __name__ == "__main__":
    print(json.dumps(main()))
