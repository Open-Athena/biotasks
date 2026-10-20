"""Seed selection and identity must not depend on a private launcher's overrides."""

import hashlib
import json

import launch_reference as launcher
import pytest


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
    monkeypatch.setattr(launcher.subprocess, "check_output", lambda *a, **k: b"archive")
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
