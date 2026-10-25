"""Cache consolidation must preserve every sealed payload and permission."""

import hashlib
import os

import pytest
from consolidate_cache import consolidate
from readback_cache import verify_local


def fixture(tmp_path):
    raw = b"immutable scientific evidence\n"
    first, second, third = (tmp_path / name for name in ("first", "second", "third"))
    first.write_bytes(raw)
    second.write_bytes(raw)
    os.link(second, third)
    for path in (first, second, third):
        path.chmod(0o640)
    row = {
        "path": "evidence",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "mode": 0o640,
    }
    return [(p, row.copy()) for p in (first, second, third)]


def test_preserve_individual_names_payloads_and_modes(tmp_path):
    paths = fixture(tmp_path)
    with (tmp_path / "journal").open("x") as journal:
        assert consolidate(paths, journal) == 2
    assert len({p.stat().st_ino for p, _ in paths}) == 1
    for path, row in paths:
        verify_local(path, row)
    with (tmp_path / "second-journal").open("x") as journal:
        assert consolidate(paths, journal) == 0


@pytest.mark.parametrize("defect", ["bytes", "mode", "symlink"])
def test_refuse_bad_original_before_any_replacement(tmp_path, defect):
    paths = fixture(tmp_path)
    original = paths[0][0].stat().st_ino
    if defect == "bytes":
        paths[1][0].write_bytes(b"changed")
    elif defect == "mode":
        paths[1][0].chmod(0o600)
    else:
        path = paths[1][0]
        path.unlink()
        path.symlink_to(paths[2][0])
    with (tmp_path / "journal").open("x") as journal:
        with pytest.raises(ValueError):
            consolidate(paths, journal)
    assert paths[0][0].stat().st_ino == original


def test_replace_failure_keeps_original_and_cleans_only_own_temporary(tmp_path, monkeypatch):
    paths = fixture(tmp_path)
    before = [p.read_bytes() for p, _ in paths]

    def refuse(*args):
        raise OSError("filesystem refused atomic replacement")

    monkeypatch.setattr(os, "replace", refuse)
    with (tmp_path / "journal").open("x") as journal:
        with pytest.raises(OSError):
            consolidate(paths, journal)
    assert [p.read_bytes() for p, _ in paths] == before
    assert not list(tmp_path.glob("*.cache-link-*"))


def test_refuse_symlink_even_if_it_aliases_the_canonical(tmp_path):
    paths = fixture(tmp_path)
    paths[1][0].unlink()
    paths[1][0].symlink_to(paths[0][0])
    with (tmp_path / "journal").open("x") as journal:
        with pytest.raises(ValueError, match="symlinks"):
            consolidate(paths[:2], journal)
