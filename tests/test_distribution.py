import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_installed_distribution_contains_and_loads_prompts(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    dist = tmp_path / "dist"
    outside = tmp_path / "outside-checkout"
    outside.mkdir()
    environment = os.environ | {"PYTHONPATH": ""}

    subprocess.run(
        ["uv", "build", "--offline", "--no-sources", "--out-dir", str(dist)],
        cwd=root,
        env=environment,
        check=True,
        timeout=60,
    )
    (wheel,) = dist.glob("*.whl")
    (sdist,) = dist.glob("*.tar.gz")
    expected = {
        path.stem: path.read_bytes() for path in (root / "src/biotasks/prompts").glob("*.md")
    }
    assert expected, "The distribution needs actual prompt assets to test"

    with zipfile.ZipFile(wheel) as archive:
        for name, content in expected.items():
            assert archive.read(f"biotasks/prompts/{name}.md") == content
    with tarfile.open(sdist) as archive:
        prefix = sdist.name.removesuffix(".tar.gz")
        for name, content in expected.items():
            member = archive.extractfile(f"{prefix}/src/biotasks/prompts/{name}.md")
            assert member is not None
            with member:
                assert member.read() == content

    venv = tmp_path / "installed"
    # Reuse locked artifact URLs; an offline requirements-file install also needs
    # registry metadata that a fresh `uv sync --locked` does not populate.
    subprocess.run(
        [
            "uv",
            "sync",
            "--locked",
            "--offline",
            "--no-dev",
            "--no-install-project",
            "--python",
            sys.executable,
        ],
        cwd=root,
        env=environment | {"UV_PROJECT_ENVIRONMENT": str(venv)},
        check=True,
        timeout=60,
    )
    scripts = venv / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    cli = scripts / ("biotasks.exe" if os.name == "nt" else "biotasks")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), "--offline", "--no-deps", str(wheel)],
        cwd=outside,
        env=environment,
        check=True,
        timeout=60,
    )
    listing = subprocess.check_output(
        [str(cli), "prompts", "list"], cwd=outside, env=environment, timeout=10
    )
    assert listing.decode().splitlines() == sorted(expected)
    for name, content in expected.items():
        assert (
            subprocess.check_output(
                [str(cli), "prompts", "show", name], cwd=outside, env=environment, timeout=10
            )
            == content
        )
        assert (
            subprocess.check_output(
                [str(python), "-I", "-m", "biotasks", "prompts", "show", name],
                cwd=outside,
                env=environment,
                timeout=10,
            )
            == content
        )
