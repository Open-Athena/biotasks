"""Seed selection and identity must not depend on a private launcher's overrides."""

import hashlib
import io
import json
import subprocess
import tarfile

import launch_reference as launcher
import pytest


def test_autonomous_seed_metadata_cannot_supply_a_legacy_task_question():
    from launch_autonomous import require_source_only_seed

    source = {"url": "https://example.org/notebook.ipynb", "source_sha256": "a" * 64}
    require_source_only_seed([source])
    legacy = {**source, "question_text": "An already-authored task"}
    with pytest.raises(ValueError, match="source metadata"):
        require_source_only_seed([legacy])
    assert legacy["question_text"] == "An already-authored task"
    for malformed in ([], [source, source], source, [None]):
        with pytest.raises(ValueError, match="one notebook source"):
            require_source_only_seed(malformed)


def fixture(monkeypatch, tmp_path):
    notebook = b'{"cells": []}'
    prefix = launcher.EXPERIMENT + "/"
    contents = {
        prefix + "case/seed.json": json.dumps(
            [{"source_sha256": hashlib.sha256(notebook).hexdigest()}]
        ).encode(),
        prefix + "case/source.ipynb": notebook,
        prefix + "iris_bootstrap.py": b"bootstrap",
        prefix + "recover_evidence.py": b"diagnostics",
    }
    monkeypatch.setattr(launcher, "frozen_file", lambda repo, revision, name: contents[name])

    def git_output(command, **kwargs):
        if command[1] == "ls-tree":
            return ("\0".join(contents) + "\0").encode()
        return b"archive"

    monkeypatch.setattr(launcher.subprocess, "check_output", git_output)
    upstream = tmp_path / "upstream.tar.gz"
    upstream.write_bytes(b"upstream")
    return (
        {
            "entrypoint": "run_autonomous.py",
            "seed_file": "case/seed.json",
            "notebook_file": "case/source.ipynb",
        },
        contents,
        upstream,
    )


def test_payload_selects_pinned_seed_and_hashes_it(monkeypatch, tmp_path):
    config, contents, upstream = fixture(monkeypatch, tmp_path)
    files = launcher.frozen_payload(
        tmp_path, revision="frozen", upstream_archive=upstream, config=config
    )
    assert files["seeds.json"] == contents[launcher.EXPERIMENT + "/case/seed.json"]
    assert (
        json.loads(files["inputs.json"])["files"]["seeds.json"]
        == hashlib.sha256(files["seeds.json"]).hexdigest()
    )
    contents[launcher.EXPERIMENT + "/case/source.ipynb"] = b"different notebook"
    with pytest.raises(ValueError, match="differs"):
        launcher.frozen_payload(
            tmp_path, revision="frozen", upstream_archive=upstream, config=config
        )


@pytest.mark.parametrize("bad", ["../seed.json", "/seed.json", "case//seed.json"])
def test_seed_path_cannot_escape_pinned_experiment(monkeypatch, tmp_path, bad):
    config, _, upstream = fixture(monkeypatch, tmp_path)
    config["seed_file"] = bad
    with pytest.raises(ValueError, match="canonical"):
        launcher.frozen_payload(
            tmp_path, revision="frozen", upstream_archive=upstream, config=config
        )


@pytest.mark.parametrize("seeds", [{"source_sha256": "x"}, [], [{}, {}]])
def test_payload_requires_one_seed(monkeypatch, tmp_path, seeds):
    config, contents, upstream = fixture(monkeypatch, tmp_path)
    contents[launcher.EXPERIMENT + "/case/seed.json"] = json.dumps(seeds).encode()
    with pytest.raises(ValueError, match="exactly one"):
        launcher.frozen_payload(
            tmp_path, revision="frozen", upstream_archive=upstream, config=config
        )


@pytest.mark.parametrize("entrypoint", ["run_autonomous.py", "run_roundtrip_diagnostic.py"])
def test_real_archive_contains_runtime_and_selected_seed_without_past_artifacts(tmp_path, entrypoint):
    prefix = launcher.EXPERIMENT + "/"
    contents = {
        "pyproject.toml": "fixture",
        "src/biotasks/prompts/prompt.md": "runtime prompt",
        prefix + "run_autonomous.py": "runtime entrypoint",
        prefix + "upstream-pin.json": "runtime pin",
        prefix + "reader-requirements.txt": "runtime requirements",
        prefix + "patches/adapter.patch": "runtime patch",
        prefix + "case/seed.json": "seed manifest",
        prefix + "case/source[1].ipynb": "original notebook",
        prefix + "case/notices[1].json": "explicit reviewed notices",
        prefix + "case/notices1.json": "unselected notices",
        prefix + "case/source1.ipynb": "different seed that a glob must not capture",
        prefix + "autonomous-runs/old/output.csv": "historical output",
        prefix + "campaign-old-result.json": "flat historical receipt",
        prefix + "other-case/source.ipynb": "another seed",
        "experiments/other-experiment/data.csv": "unrelated experiment",
    }
    for name, value in contents.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    config = {
        "entrypoint": entrypoint,
        "seed_file": "case/seed.json",
        "notebook_file": "case/source[1].ipynb",
        "source_notices_file": "case/notices[1].json",
    }
    archive = launcher.source_archive(tmp_path, "HEAD", config)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        files = {member.name for member in bundle.getmembers() if member.isfile()}
        for name in (
            prefix + "case/seed.json",
            prefix + "case/source[1].ipynb",
            prefix + "case/notices[1].json",
            prefix + "run_autonomous.py",
            prefix + "upstream-pin.json",
            prefix + "reader-requirements.txt",
            prefix + "patches/adapter.patch",
            "src/biotasks/prompts/prompt.md",
            "pyproject.toml",
        ):
            assert name in files
            assert bundle.extractfile(name).read().decode() == contents[name]
        assert prefix + "case/source1.ipynb" not in files
        assert prefix + "case/notices1.json" not in files
        assert prefix + "autonomous-runs/old/output.csv" not in files
        assert prefix + "campaign-old-result.json" not in files
        assert prefix + "other-case/source.ipynb" not in files
        assert "experiments/other-experiment/data.csv" not in files
    # Continuation workflows still need their explicitly recorded old evidence.
    full = launcher.source_archive(tmp_path, "HEAD", {"entrypoint": "run_reference_setup.py"})
    with tarfile.open(fileobj=io.BytesIO(full)) as bundle:
        assert prefix + "autonomous-runs/old/output.csv" in bundle.getnames()


@pytest.mark.parametrize("bad", ["../notices.json", "/notices.json", "case//notices.json", ".", 42])
def test_notice_payload_path_cannot_escape_pinned_experiment(monkeypatch, tmp_path, bad):
    config, _, upstream = fixture(monkeypatch, tmp_path)
    config["source_notices_file"] = bad
    with pytest.raises(ValueError, match="canonical"):
        launcher.frozen_payload(
            tmp_path, revision="frozen", upstream_archive=upstream, config=config
        )


def test_explicit_notice_file_must_be_checkpointed(monkeypatch, tmp_path):
    config, _, upstream = fixture(monkeypatch, tmp_path)
    config["source_notices_file"] = "case/missing-notices.json"
    with pytest.raises(ValueError, match="missing its pinned seed files"):
        launcher.frozen_payload(
            tmp_path, revision="frozen", upstream_archive=upstream, config=config
        )
