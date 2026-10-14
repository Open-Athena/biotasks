"""Dependency admission and controller-owned environment construction checks."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from reference_environment import validate_environment, write_environment
from test_reference import plan


@pytest.mark.parametrize("manifest,packages", [
    ('[project', []),
    ('[project]\nname="x"', []),
    ('[project]\nname="x"\nversion="1"\nrequires-python=">=3.13"\ndependencies="numpy"', []),
    (None, ["--allow-unauthenticated"]),
    (None, ["curl; echo surprise"]),
])
def test_invalid_declarations_rejected(manifest, packages):
    with pytest.raises(ValueError):
        validate_environment(manifest if manifest is not None else plan().pyproject_toml, packages)


def test_dependency_project_cannot_declare_a_build_backend():
    with pytest.raises(ValueError, match="dependency-only"):
        plan(pyproject_toml=plan().pyproject_toml + '\n[build-system]\nrequires=[]\n')


def test_materialization_is_inert_and_separates_controller_from_worker(tmp_path):
    marker = tmp_path / "must-not-exist"
    prepared = plan(stage_inputs_sh=f"touch {marker}\n", system_packages=["libgomp1"])
    write_environment(tmp_path, prepared)
    assert not marker.exists()
    assert (tmp_path / "pyproject.toml").read_text() == prepared.pyproject_toml
    assert (tmp_path / "stage-inputs.sh").read_text() == prepared.stage_inputs_sh
    setup = (tmp_path / "setup.sh").read_text()
    assert str(marker) not in setup
    assert "uv lock" in setup and "uv sync" in setup and "--locked" in setup
    assert setup.index("uv sync") < setup.index("sh -eu /work/stage-inputs.sh")
    subprocess.run(["sh", "-n", str(tmp_path / "setup.sh")], check=True)


def test_uv_creates_environment_and_lock_without_pip_in_venv(tmp_path):
    # A dependency-free fixture exercises real uv without downloads or biology.
    uv = Path(__file__).parents[2] / ".venv/bin/uv"
    project = tmp_path / "project"
    project.mkdir()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    (project / "pyproject.toml").write_text(
        f'[project]\nname="reference-fixture"\nversion="0.1.0"\nrequires-python="=={version}.*"\ndependencies=[]\n'
    )
    environment = tmp_path / "venv"
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(environment), "UV_PYTHON_DOWNLOADS": "never", "UV_CACHE_DIR": str(tmp_path / "cache")}
    for args in (["lock"], ["sync", "--locked", "--no-dev", "--no-install-project"]):
        subprocess.run([str(uv), *args, "--offline", "--project", str(project), "--python", sys.executable], env=env, check=True, capture_output=True)
    assert (project / "uv.lock").is_file()
    subprocess.run([str(environment / "bin/python"), "-c", "import sys; assert sys.prefix != sys.base_prefix"], check=True)
    assert not (environment / "bin/pip").exists()
