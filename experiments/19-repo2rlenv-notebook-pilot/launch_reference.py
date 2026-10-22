"""Build a reference-only payload from a committed revision; no network effects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

from launch_iris import EXPERIMENT, frozen_file
from run_reference import EXECUTION_PENDING


def autonomous_asset_paths(config):
    keys = ["seed_file", "notebook_file"]
    if config.get("source_notices_file") is not None:
        keys.append("source_notices_file")
    result = set()
    for key in keys:
        value = config[key]
        if not isinstance(value, str):
            raise ValueError("Autonomous assets need canonical experiment-relative paths")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
            raise ValueError("Autonomous assets need canonical experiment-relative paths")
        result.add(EXPERIMENT + "/" + value)
    return result


def source_archive(repo: Path, revision: str, config) -> bytes:
    """Fresh autonomous runs need runtime files and their seed, not past runs."""
    command = ["git", "archive", "--format=tar.gz", revision]
    if config["entrypoint"] == "run_autonomous.py":
        tracked = (
            subprocess.check_output(
                ["git", "ls-tree", "-r", "-z", "--name-only", revision], cwd=repo
            )
            .decode()
            .split("\0")
        )
        root_files = {"pyproject.toml", "uv.lock", ".python-version", "README.md", "LICENSE"}
        experiment = PurePosixPath(EXPERIMENT)
        seed_files = autonomous_asset_paths(config)
        if not seed_files.issubset(tracked):
            raise ValueError("Autonomous archive is missing its pinned seed files")
        selected = [
            path
            for path in tracked
            if path
            and (
                path in root_files
                or path.startswith("src/")
                or (
                    PurePosixPath(path).parent == experiment
                    and (
                        PurePosixPath(path).suffix in {".py", ".txt"}
                        or PurePosixPath(path).name == "upstream-pin.json"
                    )
                )
                or path.startswith(EXPERIMENT + "/patches/")
                or path in seed_files
            )
        ]
        # Literal pathspecs also support filenames containing Git glob syntax.
        command += ["--", *[":(literal)" + path for path in selected]]
    return subprocess.check_output(command, cwd=repo)


def payload(repo: Path, *, revision: str, upstream_archive: Path) -> dict[str, bytes]:
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/reference-execution.json"))
    if config["entrypoint"] != "run_reference.py":
        raise ValueError("A reference payload cannot launch another pipeline stage")
    return frozen_payload(repo, revision=revision, upstream_archive=upstream_archive, config=config)


def frozen_payload(
    repo: Path, *, revision: str, upstream_archive: Path, config
) -> dict[str, bytes]:
    """Common frozen inputs; each stage wrapper validates its own configuration."""
    if config["entrypoint"] == "run_reference.py":
        raise NotImplementedError(EXECUTION_PENDING)
    if config["entrypoint"] in {
        "run_reference_setup.py",
        "run_reference_replay.py",
        "run_notebook_grader.py",
    }:
        from run_reference_setup import check_config

        check_config(config)
    seed_path = "seeds/current.json"
    if config["entrypoint"] == "run_autonomous.py":
        seed_path = config["seed_file"]
        autonomous_asset_paths(config)
        seeds = json.loads(frozen_file(repo, revision, EXPERIMENT + "/" + seed_path))
        if not isinstance(seeds, list) or len(seeds) != 1:
            raise ValueError("Autonomous payload requires exactly one seed record")
        seed = seeds[0]
        notebook = frozen_file(repo, revision, EXPERIMENT + "/" + config["notebook_file"])
        if hashlib.sha256(notebook).hexdigest() != seed["source_sha256"]:
            raise ValueError("Pinned notebook differs from seed identity")
    files = {
        # The bootstrap auto-detects compression. Keep the existing transport key
        # while avoiding large uncompressed copies in the Iris submission client.
        "biotasks.tar": source_archive(repo, revision, config),
        "upstream.tar.gz": upstream_archive.read_bytes(),
        "seeds.json": frozen_file(repo, revision, EXPERIMENT + "/" + seed_path),
        "bootstrap.py": frozen_file(repo, revision, EXPERIMENT + "/iris_bootstrap.py"),
        "diagnostics.py": frozen_file(repo, revision, EXPERIMENT + "/recover_evidence.py"),
        "campaign-config.json": json.dumps(config, indent=2).encode(),
    }
    files["inputs.json"] = json.dumps(
        {
            "factory_revision": revision,
            "source_archive_policy": (
                "autonomous-runtime-and-seed-v1"
                if config["entrypoint"] == "run_autonomous.py"
                else "complete-checkout"
            ),
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        },
        indent=2,
    ).encode()
    return files
