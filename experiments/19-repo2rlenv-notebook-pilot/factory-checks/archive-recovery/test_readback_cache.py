"""Storage reuse must never substitute for independent remote-object verification."""

import hashlib
import importlib.util
import io
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "archive_cache_fixture", Path(__file__).with_name("readback_cache.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(data, mode=0o600):
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "mode": mode}


def test_duplicate_still_reads_its_distinct_remote_object_and_preserves_all_paths(tmp_path):
    reads, cache, data = [], {}, b"original scientific artifact"

    def source(name, payload=data):
        def open_source():
            reads.append(name)
            return io.BytesIO(payload)

        return open_source

    first, second = tmp_path / "first.bin", tmp_path / "second.bin"
    MODULE.store(source("remote-a"), first, row(data), cache)
    result = MODULE.store(source("remote-b"), second, row(data), cache)
    assert reads == ["remote-a", "remote-b"]
    assert result["remote_object_read_now"] and "hardlink" in result["method"]
    assert first.stat().st_ino == second.stat().st_ino
    assert first.read_bytes() == second.read_bytes() == data


def test_different_modes_do_not_share_an_inode(tmp_path):
    cache, data = {}, b"same content, different original mode"
    a, b = tmp_path / "a", tmp_path / "b"
    MODULE.store(lambda: io.BytesIO(data), a, row(data, 0o600), cache)
    MODULE.store(lambda: io.BytesIO(data), b, row(data, 0o644), cache)
    assert a.stat().st_ino != b.stat().st_ino
    assert a.stat().st_mode & 0o777 == 0o600 and b.stat().st_mode & 0o777 == 0o644


def test_corrupt_duplicate_remote_is_not_hidden_by_a_matching_local_cache(tmp_path):
    cache, data = {}, b"expected"
    MODULE.store(lambda: io.BytesIO(data), tmp_path / "a", row(data), cache)
    with pytest.raises(ValueError, match="sealed identity"):
        MODULE.store(lambda: io.BytesIO(b"corrupt!"), tmp_path / "b", row(data), cache)
    assert not (tmp_path / "b").exists() and (tmp_path / "a").read_bytes() == data


def test_changed_local_cache_is_not_reused_after_a_valid_remote_read(tmp_path):
    cache, data = {}, b"expected"
    MODULE.store(lambda: io.BytesIO(data), tmp_path / "a", row(data), cache)
    (tmp_path / "a").write_bytes(b"corrupt!")
    with pytest.raises(ValueError, match="cache identity"):
        MODULE.store(lambda: io.BytesIO(data), tmp_path / "b", row(data), cache)
    assert not (tmp_path / "b").exists()


def test_bad_first_read_preserves_partial_and_refuses_silent_overwrite(tmp_path):
    cache, data = {}, b"expected"
    with pytest.raises(ValueError):
        MODULE.store(lambda: io.BytesIO(b"bad"), tmp_path / "a", row(data), cache)
    assert (tmp_path / "a.readback-partial").read_bytes() == b"bad"
    with pytest.raises(ValueError, match="Preserve interrupted"):
        MODULE.store(lambda: io.BytesIO(data), tmp_path / "a", row(data), cache)
    assert not (tmp_path / "a").exists() and not cache
