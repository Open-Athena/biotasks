"""Dependency admission and controller-owned environment construction checks."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from reference_environment import validate_environment, write_environment


def environment(**changes):
    """Environment helper fixture, independent of the preparation response."""
    return SimpleNamespace(
        **{
            "pyproject_toml": '[project]\nname="reference"\nversion="0.1.0"\nrequires-python=">=3.13,<3.14"\ndependencies=[]\n',
            "system_packages": [],
            "stage_inputs_sh": "",
            **changes,
        }
    )


@pytest.mark.parametrize(
    "dependency,sources",
    [
        ("example @ git+https://example.invalid/project@abcdef", ""),
        ("example @ git+ssh://git@example.invalid/project@abcdef", ""),
        (
            "example",
            '\n[tool.uv.sources]\nexample = { git = "https://example.invalid/project", rev = "abcdef" }\n',
        ),
        (
            "example",
            '\n[tool.uv.sources]\nexample = [{ git = "https://example.invalid/project", marker = "sys_platform == \'linux\'" }]\n',
        ),
    ],
)
def test_git_dependency_requires_declared_installer_tool(dependency, sources):
    import json

    project = (
        environment().pyproject_toml.replace(
            "dependencies=[]", "dependencies=[" + json.dumps(dependency) + "]"
        )
        + sources
    )
    with pytest.raises(ValueError, match="Git-based dependencies require git"):
        validate_environment(project, [])
    for declaration in ["git", "git=1:2.39.5-0", "git:amd64"]:
        validate_environment(project, [declaration])


def test_non_git_requirements_do_not_force_installer_packages():
    project = environment().pyproject_toml.replace(
        "dependencies=[]", 'dependencies=["example @ https://example.invalid/package.whl"]'
    )
    validate_environment(project, [])


@pytest.mark.parametrize(
    "manifest,packages",
    [
        ("[project", []),
        ('project="wrong type"', []),
        ("project=[]", []),
        ('[project]\nname="x"', []),
        ('[project]\nname="x"\nversion="1"\nrequires-python=">=3.13"\ndependencies="numpy"', []),
        (None, ["--allow-unauthenticated"]),
        (None, ["curl; echo surprise"]),
    ],
)
def test_invalid_declarations_rejected(manifest, packages):
    with pytest.raises(ValueError):
        validate_environment(
            manifest if manifest is not None else environment().pyproject_toml, packages
        )


def test_dependency_project_cannot_declare_a_build_backend():
    with pytest.raises(ValueError, match="dependency-only"):
        validate_environment(environment().pyproject_toml + "\n[build-system]\nrequires=[]\n", [])


def test_materialization_is_inert_and_separates_controller_from_worker(tmp_path):
    marker = tmp_path / "must-not-exist"
    prepared = environment(stage_inputs_sh=f"touch {marker}\n", system_packages=["libgomp1"])
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
    env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(environment),
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_CACHE_DIR": str(tmp_path / "cache"),
    }
    for args in (["lock"], ["sync", "--locked", "--no-dev", "--no-install-project"]):
        subprocess.run(
            [str(uv), *args, "--offline", "--project", str(project), "--python", sys.executable],
            env=env,
            check=True,
            capture_output=True,
        )
    assert (project / "uv.lock").is_file()
    subprocess.run(
        [str(environment / "bin/python"), "-c", "import sys; assert sys.prefix != sys.base_prefix"],
        check=True,
    )
    assert not (environment / "bin/pip").exists()


def test_staging_receipt_verifies_files_and_rejects_changed_data(tmp_path):
    import hashlib
    import json

    from reference_remote import verify_staging

    data = tmp_path / "input.tsv"
    data.write_text("real input fixture")
    receipt = tmp_path / "receipt.json"
    record = {
        "local_path": str(data),
        "source": "synthetic test fixture",
        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
    }
    receipt.write_text(json.dumps({"files": [record]}))
    assert verify_staging(receipt, roots=(tmp_path,))["files"] == 1
    data.write_text("changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_staging(receipt, roots=(tmp_path,))
    receipt.write_text('{"files": [{}]}')
    with pytest.raises(ValueError, match="require"):
        verify_staging(receipt, roots=(tmp_path,))
