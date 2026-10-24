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
    from biotasks.validation.planning import code_files

    validation = code_files()
    assert "worker/setup_controller.sh" in validation
    from biotasks.generation.resources import code_files as generation_files

    generation = generation_files()
    assert "worker/generation_entry.py.txt" in generation
    assert "package-acquisition.json" in generation

    with zipfile.ZipFile(wheel) as archive:
        for name, content in expected.items():
            assert archive.read(f"biotasks/prompts/{name}.md") == content
        for name, content in validation.items():
            assert archive.read("biotasks/validation/" + name) == content
        for name, content in generation.items():
            assert archive.read("biotasks/generation/" + name) == content
    with tarfile.open(sdist) as archive:
        prefix = sdist.name.removesuffix(".tar.gz")
        for name, content in expected.items():
            member = archive.extractfile(f"{prefix}/src/biotasks/prompts/{name}.md")
            assert member is not None
            with member:
                assert member.read() == content
        for name, content in validation.items():
            member = archive.extractfile(f"{prefix}/src/biotasks/validation/" + name)
            assert member is not None
            assert member.read() == content
        for name, content in generation.items():
            member = archive.extractfile(f"{prefix}/src/biotasks/generation/{name}")
            assert member is not None
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
    import json

    worker_resources = subprocess.check_output(
        [
            str(python),
            "-I",
            "-c",
            "import json; from biotasks.validation.planning import code_files; from biotasks.validation.files import content_sha; print(json.dumps({n:content_sha(v) for n,v in code_files().items()}))",
        ],
        cwd=outside,
        env=environment,
        timeout=10,
    )
    from biotasks.validation.files import content_sha

    assert json.loads(worker_resources) == {n: content_sha(v) for n, v in validation.items()}
    generation_resources = subprocess.check_output(
        [
            str(python),
            "-I",
            "-c",
            "import json; from biotasks.generation.resources import code_files; from biotasks.validation.files import content_sha; print(json.dumps({n:content_sha(v) for n,v in code_files().items()}))",
        ],
        cwd=outside,
        env=environment,
        timeout=10,
    )
    assert json.loads(generation_resources) == {n: content_sha(v) for n, v in generation.items()}
    identities = json.loads(
        subprocess.check_output(
            [str(cli), "generate", "identities"], cwd=outside, env=environment, timeout=10
        )
    )
    from biotasks.generation.resources import code_identity as generation_identity

    assert identities["generation_code_identity"] == generation_identity()
    # A real wheel lives beside its own dependencies. Only its BioTasks
    # namespace may enter the separately configured SDK interpreter.
    site = Path(
        subprocess.check_output(
            [str(python), "-I", "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
            cwd=outside,
            env=environment,
            timeout=10,
        )
        .decode()
        .strip()
    )
    (site / "sdk_dependency.py").write_text("origin='wrong-main-environment'\n")
    sdk = tmp_path / "sdk-imports"
    sdk.mkdir()
    (sdk / "sdk_dependency.py").write_text("origin='configured-sdk'\n")
    for name in ("iris", "rigging"):
        (sdk / name).mkdir()
        (sdk / name / "__init__.py").write_text(
            "import sdk_dependency\nassert sdk_dependency.origin=='configured-sdk'\n"
        )
    probe = "import sys;from pathlib import Path;from biotasks.validation.bridge import call;v=call({'python':sys.executable},{'action':'fingerprint'},Path(sys.argv[1]));assert set(v['source'])=={'iris','rigging'}"
    subprocess.run(
        [str(python), "-I", "-c", probe, str(tmp_path / "installed-bridge.log")],
        cwd=outside,
        env=environment | {"PYTHONPATH": str(sdk)},
        check=True,
        timeout=30,
    )
    generation_probe = probe.replace(
        "biotasks.validation.bridge", "biotasks.generation.generation_bridge"
    )
    subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            generation_probe,
            str(tmp_path / "installed-generation-bridge.log"),
        ],
        cwd=outside,
        env=environment | {"PYTHONPATH": str(sdk)},
        check=True,
        timeout=30,
    )
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
