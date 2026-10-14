"""Controller-owned Python environment setup; never execute during preparation."""

import re
import shlex
import tomllib
from pathlib import Path

UV_VERSION = "0.12.21"


def validate_environment(pyproject_toml: str, system_packages: list[str]) -> None:
    document = tomllib.loads(pyproject_toml)
    project = document.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("project must be a TOML table")
    for key in ("name", "version", "requires-python"):
        if not isinstance(project.get(key), str) or not project[key].strip():
            raise ValueError(f"pyproject.toml requires project.{key}")
    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list) or any(
        not isinstance(item, str) or not item.strip() for item in dependencies
    ):
        raise ValueError("project.dependencies must be an array of requirement strings")
    if "build-system" in document or project.get("dynamic"):
        raise ValueError("Use a dependency-only project with static dependencies, no build system")
    for package in system_packages:
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?(?:=[A-Za-z0-9.+:~_-]+)?", package):
            raise ValueError("System packages must be Debian package names, optionally versioned")


def setup_script(system_packages: list[str], *, has_staging: bool = True) -> str:
    lines = ["#!/bin/sh", "set -eu", "cd /work", "export DEBIAN_FRONTEND=noninteractive"]
    if system_packages:
        lines += ["apt-get update", "apt-get install -y --no-install-recommends " + shlex.join(system_packages)]
    lines += [
        # The base image has pip; it bootstraps only the pinned uv executable.
        f"python -m pip install --disable-pip-version-check uv=={UV_VERSION}",
        "export UV_PROJECT_ENVIRONMENT=/work/venv",
        "export UV_PYTHON_DOWNLOADS=never",
        'uv lock --project /work/environment --python "$(command -v python)"',
        'uv sync --project /work/environment --locked --no-dev --no-install-project --python "$(command -v python)"',
        "uv pip freeze --python /work/venv/bin/python > /work/environment/environment.txt",
        "export PATH=/work/venv/bin:$PATH",
        "rm -f /work/setup-inputs.json",
        "sh -eu /work/stage-inputs.sh",
    ]
    if not has_staging:
        lines.append("printf '%s\\n' '{\"files\": []}' > /work/setup-inputs.json")
    lines.append("python /work/remote.py verify-staging /work/setup-inputs.json")
    return "\n".join(lines) + "\n"


def write_environment(directory: Path, plan) -> None:
    validate_environment(plan.pyproject_toml, plan.system_packages)
    (directory / "pyproject.toml").write_text(plan.pyproject_toml)
    (directory / "stage-inputs.sh").write_text(plan.stage_inputs_sh)
    (directory / "setup.sh").write_text(setup_script(plan.system_packages, has_staging=bool(plan.stage_inputs_sh.strip())))
