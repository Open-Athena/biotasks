"""Build a reference-only payload from a committed revision; no network effects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

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
    if config["entrypoint"] == "run_reference_setup.py":
        from run_reference_setup import check_config
        check_config(config)
    files = {
        "biotasks.tar": subprocess.check_output(["git", "archive", revision], cwd=repo),
        "upstream.tar.gz": upstream_archive.read_bytes(),
        "seeds.json": frozen_file(repo, revision, EXPERIMENT + "/seeds/current.json"),
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
