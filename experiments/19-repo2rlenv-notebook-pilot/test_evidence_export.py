"""Streaming export preserves exact bytes and refuses credentials/symlinks."""

import hashlib
import json

import pytest
from iris_bootstrap import export


def test_export_download_checks_every_file(tmp_path, monkeypatch):
    for name in ("GLM_BULK_TOKEN", "DAYTONA_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (source / "large").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    (source / "small").write_text("data")
    export(source, target.as_uri())
    result = json.loads((target / "export-manifest.json").read_text())
    assert result["download_checked"]
    assert [r["path"] for r in result["files"]] == ["large", "small"]
    for record in result["files"]:
        data = (target / record["path"]).read_bytes()
        assert len(data) == record["bytes"] and hashlib.sha256(data).hexdigest() == record["sha256"]


def test_export_refuses_secret_spanning_chunks(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "fixture-secret-only")
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (source / "bad").write_bytes(b"x" * (1024 * 1024 - 5) + b"fixture-secret-only")
    with pytest.raises(ValueError, match="Credential detected"):
        export(source, target.as_uri())
    assert not (target / "export-manifest.json").exists()


def test_export_refuses_symlinks(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "link").symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="symlinks"):
        export(source, (tmp_path / "target").as_uri())
