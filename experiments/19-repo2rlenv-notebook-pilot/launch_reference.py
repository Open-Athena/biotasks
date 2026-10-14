"""Build a reference-only payload from a committed revision; no network effects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from launch_iris import EXPERIMENT, frozen_file


def payload(repo: Path, *, revision: str, upstream_archive: Path) -> dict[str, bytes]:
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/reference-execution.json"))
    if config["entrypoint"] != "run_reference.py":
        raise ValueError("A reference payload cannot launch another pipeline stage")
    files = {
        "biotasks.tar": subprocess.check_output(["git", "archive", revision], cwd=repo),
        "upstream.tar.gz": upstream_archive.read_bytes(),
        "seeds.json": frozen_file(repo, revision, EXPERIMENT + "/seeds/current.json"),
        "bootstrap.py": frozen_file(repo, revision, EXPERIMENT + "/iris_bootstrap.py"),
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
