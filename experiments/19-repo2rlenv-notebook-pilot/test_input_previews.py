"""Raw input observations are bounded evidence, not inferred parsing rules."""

import gzip
import hashlib
import json

import pytest
from reference_remote import input_preview, snapshot_inputs, verify_staging


@pytest.mark.parametrize("compressed", [False, True])
def test_receipt_shows_actual_leading_records_and_keeps_original_hash(tmp_path, compressed):
    raw = b"alpha\t4\t9\nbeta\t12\t18\n"
    stored = gzip.compress(raw) if compressed else raw
    path = tmp_path / "input"
    path.write_bytes(stored)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"files": [{"local_path": str(path), "source": "fixture://original"}]})
    )
    receipt_path = tmp_path / "receipt.json"
    receipt = snapshot_inputs(manifest, receipt_path, roots=(tmp_path,))
    item = receipt["files"][0]
    assert item["sha256"] == hashlib.sha256(stored).hexdigest()
    assert item["input_preview"]["text"] == raw.decode()
    assert item["input_preview"]["sample_sha256"] == hashlib.sha256(raw).hexdigest()
    assert item["input_preview"]["compression"] == ("gzip" if compressed else "none")
    assert not item["input_preview"]["byte_prefix_truncated"]
    assert path.read_bytes() == stored
    assert verify_staging(receipt_path, roots=(tmp_path,))["files"] == 1
    # Preview metadata cannot redefine the original byte identity.
    path.write_bytes(stored + b"changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_staging(receipt_path, roots=(tmp_path,))


@pytest.mark.parametrize("compressed", [False, True])
def test_preview_bounds_decompressed_bytes_and_reports_incomplete_samples(tmp_path, compressed):
    raw = b"record\n" * 100_000
    path = tmp_path / "input"
    path.write_bytes(gzip.compress(raw) if compressed else raw)
    preview = input_preview(path)
    assert preview["sampled_bytes"] == 4096
    assert preview["byte_prefix_truncated"]
    assert preview["displayed_lines_truncated"]
    assert preview["text"] == "record\n" * 5


@pytest.mark.parametrize("raw", [b"\x00binary\xff", b"\xff\xfe\x80", b"\x1fcontrol"])
def test_non_utf8_and_control_bytes_are_not_presented_as_text(tmp_path, raw):
    path = tmp_path / "data"
    path.write_bytes(raw)
    preview = input_preview(path)
    assert preview["status"] == "raw_hex_prefix"
    assert preview["hex"] == raw.hex()
    assert "text" not in preview


def test_broken_compression_is_an_observation_not_a_schema_claim(tmp_path):
    path = tmp_path / "broken"
    path.write_bytes(b"\x1f\x8b")
    preview = input_preview(path)
    assert preview["status"] == "unavailable"
    assert preview["error_type"] == "EOFError"
