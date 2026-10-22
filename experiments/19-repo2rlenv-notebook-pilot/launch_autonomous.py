"""Build the frozen autonomous payload from a committed seed/config; no paid work."""

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath

from launch_iris import EXPERIMENT, frozen_file
from launch_reference import frozen_payload


def require_source_only_seed(seeds):
    if not isinstance(seeds, list) or len(seeds) != 1 or not isinstance(seeds[0], dict):
        raise ValueError("Autonomous execution requires one notebook source record")
    if "question_text" in seeds[0]:
        raise ValueError(
            "Autonomous seeds must contain source metadata, not a legacy authored question_text"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--revision", required=True)
    parser.add_argument("--config", required=True, help="Path relative to the experiment directory")
    parser.add_argument("--upstream-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config_path = PurePosixPath(args.config)
    if config_path.is_absolute() or ".." in config_path.parts or str(config_path) != args.config:
        raise ValueError("Config must be a canonical experiment-relative path")
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", "--end-of-options", args.revision + "^{commit}"],
        cwd=args.repo,
        text=True,
    ).strip()
    config = json.loads(frozen_file(args.repo, revision, EXPERIMENT + "/" + args.config))
    if config["entrypoint"] != "run_autonomous.py":
        raise ValueError("Autonomous campaign configuration required")
    require_source_only_seed(
        json.loads(frozen_file(args.repo, revision, EXPERIMENT + "/" + config["seed_file"]))
    )
    files = frozen_payload(
        args.repo, revision=revision, upstream_archive=args.upstream_archive, config=config
    )
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (args.output / name).write_bytes(content)
    print(
        json.dumps(
            {
                "factory_revision": revision,
                "campaign": config["campaign"],
                "payload": str(args.output),
                "submitted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
