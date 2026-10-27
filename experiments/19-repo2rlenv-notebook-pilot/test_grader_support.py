"""Shared parsing stays byte-identical across authors, controls and packaging."""

import importlib.util
import json

import grading_remote
import pytest
from grader_support import MANIFEST, MODULE, capture_support, load_support, support_interface


def test_capture_is_complete_repeatable_and_exposes_actual_source(tmp_path):
    root = tmp_path / "grading"
    metadata = capture_support(root)
    assert capture_support(root) == metadata == load_support(root)
    interface = support_interface(root)
    assert interface["source"] == (root / MODULE).read_text()
    assert interface["sha256"] == metadata["sha256"]
    assert "scientific comparisons" in interface["scope"]


@pytest.mark.parametrize(
    "change", ["source", "hash", "missing_source", "missing_manifest", "symlink"]
)
def test_changed_or_incomplete_support_is_refused(tmp_path, change):
    metadata = capture_support(tmp_path)
    if change == "source":
        (tmp_path / MODULE).write_text("raise RuntimeError('changed')")
    elif change == "hash":
        (tmp_path / MANIFEST).write_text(json.dumps({**metadata, "sha256": "a" * 64}))
    elif change == "missing_source":
        (tmp_path / MODULE).unlink()
    elif change == "missing_manifest":
        (tmp_path / MANIFEST).unlink()
    else:
        other = tmp_path / "other.py"
        (tmp_path / MODULE).rename(other)
        (tmp_path / MODULE).symlink_to(other)
    with pytest.raises(ValueError):
        load_support(tmp_path, metadata)


def test_expected_identity_cannot_disappear_as_legacy(tmp_path):
    assert load_support(tmp_path) is None
    with pytest.raises(ValueError):
        load_support(tmp_path, {"sha256": "a" * 64})


@pytest.mark.parametrize("name", [MODULE, MANIFEST])
def test_capture_and_legacy_read_refuse_dangling_links(tmp_path, name):
    root = tmp_path / "grading"
    root.mkdir()
    outside = tmp_path / "must-not-be-created"
    (root / name).symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic links"):
        capture_support(root)
    with pytest.raises(ValueError, match="symbolic links"):
        load_support(root)
    assert not outside.exists()


def test_remote_case_uses_exact_reader_and_refuses_tampering(tmp_path, monkeypatch):
    root, case = tmp_path / "private", tmp_path / "case"
    root.mkdir()
    case.mkdir()
    metadata = capture_support(root)
    monkeypatch.setattr(grading_remote, "PRIVATE", root)
    monkeypatch.setattr(grading_remote, "CASE", case)
    monkeypatch.setattr(grading_remote, "TABLE_SUPPORT", root / MODULE)
    assert grading_remote.stage_parsing_support() == metadata
    assert (case / MODULE).read_bytes() == (root / MODULE).read_bytes()
    assert (case / MODULE).stat().st_mode & 0o777 == 0o444
    spec = importlib.util.spec_from_file_location("captured_parser", case / MODULE)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    table = tmp_path / "output.csv"
    table.write_text('id,value\n"a,b",1.000\n\n')
    assert reader.read_delimited_table(table, allow_blank_records=True) == (
        ["id", "value"],
        [["a,b", "1.000"]],
    )
    (root / MODULE).write_text("# tampered support\n")
    with pytest.raises(ValueError, match="identity changed"):
        grading_remote.stage_parsing_support()
