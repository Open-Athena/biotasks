"""Package only the separately configured setup/test stage from a Git checkpoint."""
import json
from pathlib import Path

from launch_iris import EXPERIMENT, frozen_file
from launch_reference import frozen_payload


def payload(repo: Path, *, revision: str, upstream_archive: Path):
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/reference-setup.json"))
    if config.get("entrypoint") != "run_reference_setup.py":
        raise ValueError("Setup payload cannot launch another pipeline stage")
    return frozen_payload(repo, revision=revision, upstream_archive=upstream_archive, config=config)
