"""Build a reference-only payload from a committed revision; no network effects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

from launch_iris import EXPERIMENT, frozen_file
from run_reference import EXECUTION_PENDING


def payload(repo: Path, *, revision: str, upstream_archive: Path) -> dict[str, bytes]:
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/reference-execution.json"))
    if config["entrypoint"] != "run_reference.py":
        raise ValueError("A reference payload cannot launch another pipeline stage")
    return frozen_payload(repo, revision=revision, upstream_archive=upstream_archive, config=config)


def frozen_payload(repo: Path, *, revision: str, upstream_archive: Path, config) -> dict[str, bytes]:
    """Common frozen inputs; each stage wrapper validates its own configuration."""
    if config["entrypoint"] == "run_reference.py":
        raise NotImplementedError(EXECUTION_PENDING)
    if config["entrypoint"] in {"run_reference_setup.py", "run_reference_replay.py", "run_notebook_grader.py"}:
        from run_reference_setup import check_config
        check_config(config)
    seed_path = "seeds/current.json"
    if config["entrypoint"] == "run_autonomous.py":
        seed_path = config["seed_file"]
        for value in (seed_path, config["notebook_file"]):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or str(path) != value:
                raise ValueError("Autonomous seed paths must be canonical experiment-relative paths")
        seed = json.loads(frozen_file(repo, revision, EXPERIMENT + "/" + seed_path))
        notebook = frozen_file(repo, revision, EXPERIMENT + "/" + config["notebook_file"])
        if hashlib.sha256(notebook).hexdigest() != seed["source_sha256"]:
            raise ValueError("Pinned notebook differs from seed identity")
    files = {
        # The bootstrap auto-detects compression. Keep the existing transport key
        # while avoiding large uncompressed copies in the Iris submission client.
        "biotasks.tar": subprocess.check_output(
            ["git", "archive", "--format=tar.gz", revision], cwd=repo
        ),
        "upstream.tar.gz": upstream_archive.read_bytes(),
        "seeds.json": frozen_file(repo, revision, EXPERIMENT + "/" + seed_path),
        "bootstrap.py": frozen_file(repo, revision, EXPERIMENT + "/iris_bootstrap.py"),
        "diagnostics.py": frozen_file(repo, revision, EXPERIMENT + "/recover_evidence.py"),
        "campaign-config.json": json.dumps(config, indent=2).encode(),
    }
    files["inputs.json"] = json.dumps(
        {
            "factory_revision": revision,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        },
        indent=2,
    ).encode()
    return files
