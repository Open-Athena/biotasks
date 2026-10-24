"""Synthetic binary/archive boundaries; no remote acquisition or native code."""

import hashlib
import io
import tarfile
import urllib.request
import zipfile

import pytest

from biotasks.generation import source
from biotasks.validation.files import (
    ValidationError,
    content_sha,
    inventory,
    read_json,
    sha,
    write_json,
)
from biotasks.validation.planning import UPSTREAM


@pytest.fixture
def acquired(tmp_path, monkeypatch):
    raw = b"Synthetic source never imported\n"
    row = {
        "path": "src/repo2rlenv/__init__.py",
        "bytes": len(raw),
        "sha256": content_sha(raw),
        "git_blob": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
    }
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("prefix/" + row["path"])
        member.size = len(raw)
        stream.addfile(member, io.BytesIO(raw))
    wheel = tmp_path / "writer.whl"
    with zipfile.ZipFile(wheel, "w") as stream:
        stream.writestr("tomli_w/__init__.py", b"# Synthetic writer, never imported\n")
    expected = {"revision": UPSTREAM, "files": [row]}
    writer = {
        "bytes": wheel.stat().st_size,
        "sha256": sha(wheel),
        "wheel": "writer.whl",
        "source": "https://unused.invalid/writer.whl",
    }
    monkeypatch.setattr(source, "specification", lambda: (expected, writer))
    monkeypatch.setattr(source, "ARCHIVES", {sha(archive)})
    extra = tmp_path / "reference-writer"
    (extra / "tomli_w").mkdir(parents=True)
    (extra / "tomli_w/__init__.py").write_bytes(b"# Synthetic writer, never imported\n")
    monkeypatch.setattr(source, "writer_inventory", lambda: inventory(extra))
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: pytest.fail("No network in source tests")
    )
    return archive, wheel, tmp_path / "cache"


def test_source_and_dependency_acquired_without_execution_and_resume_is_inert(acquired):
    archive, writer, output = acquired
    result = source.acquire(output, archive=archive, dependency=writer)
    assert not result["package_executed"] and result["model_calls"] == result["remote_jobs"] == 0
    before = inventory(output)
    assert source.acquire(output) == result
    assert inventory(output) == before
    config = source.configuration(output)
    assert config["acquisition"]["sha256"] == sha(output / "source-manifest.json")


@pytest.mark.parametrize("kind", ["member", "extra", "writer", "receipt", "manifest"])
def test_changed_acquired_cache_is_rejected(acquired, kind):
    archive, writer, output = acquired
    source.acquire(output, archive=archive, dependency=writer)
    if kind == "member":
        (output / "source/src/repo2rlenv/__init__.py").write_text("changed")
    elif kind == "extra":
        (output / "source/unreviewed.py").write_text("extra")
    elif kind == "writer":
        (output / "extra_modules/tomli_w/__init__.py").write_text("changed")
    elif kind == "receipt":
        receipt = read_json(output / "receipt.json")
        receipt["package_executed"] = True
        write_json(output / "receipt.json", receipt)
    else:
        (output / "source-manifest.json").write_text("{}")
    with pytest.raises(ValidationError):
        source.acquire(output)


def test_unknown_archive_and_wheel_do_not_become_ready_cache(acquired):
    archive, writer, output = acquired
    archive.write_bytes(b"unknown archive")
    with pytest.raises(ValidationError, match="Unknown official archive"):
        source.acquire(output, archive=archive, dependency=writer)
    assert not output.exists() and output.with_name(output.name + ".staging").exists()


def test_writer_digest_failure_holds_without_install(acquired):
    archive, writer, output = acquired
    writer.write_bytes(b"unknown wheel")
    with pytest.raises(ValidationError, match="Pinned writer wheel changed"):
        source.acquire(output, archive=archive, dependency=writer)
    assert not output.exists()


def test_interrupted_acquisition_is_retained_for_inspection(acquired):
    _, _, output = acquired
    stage = output.with_name(output.name + ".staging")
    stage.mkdir()
    (stage / "partial").write_text("preserve")
    with pytest.raises(ValidationError, match="Interrupted acquisition retained"):
        source.acquire(output)
    assert (stage / "partial").read_text() == "preserve"


@pytest.mark.parametrize("kind", ["duplicate", "symlink", "traversal", "wrong-bytes"])
def test_member_identity_and_archive_paths_are_not_inferred(acquired, monkeypatch, kind):
    archive, _, output = acquired
    expected, _ = source.specification()
    row = expected["files"][0]
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("prefix/" + row["path"])
        data = b"Synthetic source never imported\n"
        if kind == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
        elif kind == "traversal":
            member.name = "prefix/../escape"
        elif kind == "wrong-bytes":
            data = b"X" * len(data)
        member.size = len(data)
        stream.addfile(member, io.BytesIO(data))
        if kind == "duplicate":
            stream.addfile(member, io.BytesIO(data))
    monkeypatch.setattr(source, "ARCHIVES", {sha(archive)})
    with pytest.raises(ValidationError):
        source.unpack_source(archive, output)
