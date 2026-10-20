import hashlib
import json

import pytest

from biotasks.data_profile import profile_file, profile_inputs


def test_checks_source_bytes_without_selecting_task_or_inferring_types(tmp_path):
    raw = b"id,value\na,2\nb,3\n"
    (tmp_path / "sample.csv").write_bytes(raw)
    expected = hashlib.md5(raw).hexdigest()
    report = profile_inputs(tmp_path, [{"path": "sample.csv", "checksums": {"md5": expected}}])
    record = report["files"][0]
    assert record["digests"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert record["source_identity_status"] == "verified"
    assert record["structure"]["first_record"] == ["id", "value"]
    assert record["structure"]["records_after_first"] == 2
    assert record["structure"]["first_record_is_header"] == "not inferred"
    assert report["scientific_analysis_executed"] is False
    assert "analysis_scope" not in json.dumps(report)
    with pytest.raises(ValueError, match="checksum"):
        profile_file(tmp_path, "sample.csv", {"md5": "0" * 32})


def test_sampled_rows_are_not_reported_as_whole_dataset_size(tmp_path):
    (tmp_path / "many.tsv").write_text("id\tvalue\n" + "a\t2\n" * 1000)
    structure = profile_file(tmp_path, "many.tsv")["structure"]
    assert structure["rows_inspected"] == 100
    assert structure["records_after_first"] is None


def test_unknown_and_missing_reader_stay_unknown(tmp_path, monkeypatch):
    (tmp_path / "matrix.bin").write_bytes(b"opaque")
    assert profile_file(tmp_path, "matrix.bin")["structure"]["kind"] == "unknown"
    (tmp_path / "matrix.h5").write_bytes(b"opaque")

    def missing(_name):
        raise ImportError("reader absent")

    monkeypatch.setattr("biotasks.data_profile.importlib.import_module", missing)
    assert profile_file(tmp_path, "matrix.h5")["structure"] == {
        "kind": "unknown",
        "reason": "Structural inspection did not complete",
        "error_type": "ImportError",
    }


def test_rejects_path_escape_and_symlink(tmp_path):
    (tmp_path / "source").write_text("input")
    (tmp_path / "link").symlink_to(tmp_path / "source")
    for path in ("../source", "/source", "link"):
        with pytest.raises(ValueError):
            profile_file(tmp_path, path)
