"""Freeze a saved-artifact coverage pass without invoking reference execution."""

import json

from launch_iris import EXPERIMENT, frozen_file
from launch_reference import frozen_payload


def payload(repo, *, revision, upstream_archive):
    config = json.loads(frozen_file(repo, revision, EXPERIMENT + "/coverage-inputs.json"))
    if config["entrypoint"] != "run_coverage.py":
        raise ValueError("Coverage payload cannot launch another pipeline stage")
    return frozen_payload(repo, revision=revision, upstream_archive=upstream_archive, config=config)
