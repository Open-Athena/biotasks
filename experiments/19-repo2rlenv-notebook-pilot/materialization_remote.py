"""Execute worker-generated derivations and an oracle with private answers hidden."""

import json
import shutil
from pathlib import Path

from grading_remote import AUTHOR, hashes, owned, run_as

PRIVATE = Path("/work/grading-private")
ORACLE = 18004


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
    result = {"status": "incomplete", "derivation": execution}
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
                + json.dumps({"missing": sorted(expected - set(actual)),
                              "unexpected": sorted(set(actual) - expected)})
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
                    "for p in ['/work/reference', '/work/author', '/work/grading-private']:\n"
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
        result["status"] = "executed_requires_scientific_validation"
        return result
    finally:
        verify_sources(sources)
        if hashes(Path("/work/reference")) != original:
            raise ValueError("Original reference changed")


if __name__ == "__main__":
    print(json.dumps(main()))
