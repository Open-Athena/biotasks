"""Serialization observations must not become semantic acceptance."""

import hashlib

import pytest
from replay_tables import observe_tables, table_profile


def test_order_and_csv_serialization_only(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("id,value\nx,1\ny,2\nx,1\n")
    b.write_bytes(b'"id","value"\r\nx,1\r\nx,1\r\ny,2\r\n')
    assert table_profile(a) == table_profile(b)
    b.write_text("id,value\nx,1\ny,2\ny,2\n")
    assert table_profile(a) != table_profile(b)
    b.write_text("value,id\nx,1\ny,2\nx,1\n")
    assert table_profile(a) != table_profile(b)
    b.write_text("id,value\nx,1\ny,3\nx,1\n")
    assert table_profile(a) != table_profile(b)


def test_observation_does_not_assert_scientific_equivalence(tmp_path):
    baseline, replay = tmp_path / "base", tmp_path / "replay"
    baseline.mkdir()
    replay.mkdir()
    source = b"position\na\nb\n"
    (baseline / "sequence.csv").write_bytes(source)
    (replay / "sequence.csv").write_text("position\nb\na\n")
    comparisons = [
        {
            "path": "sequence.csv",
            "byte_identical": False,
            "baseline_sha256": hashlib.sha256(source).hexdigest(),
        }
    ]
    observe_tables(comparisons, baseline, replay)
    observation = comparisons[0]["table_observation"]
    assert observation["same_header_and_row_multiset"]
    assert observation["scientific_equivalence_established"] is False
    comparisons[0]["baseline_sha256"] = "wrong"
    with pytest.raises(ValueError, match="identity"):
        observe_tables(comparisons, baseline, replay)


@pytest.mark.parametrize("extension", ["gz", "bz2", "xz"])
def test_compressed_tables_preserve_observations(tmp_path, extension):
    import bz2
    import gzip
    import lzma

    source = tmp_path / "rows.tsv"
    source.write_bytes(b"id\tvalue\nx\t1\ny\t2\n")
    target = tmp_path / ("rows.tsv." + extension)
    compress = {"gz": gzip.compress, "bz2": bz2.compress, "xz": lzma.compress}[extension]
    target.write_bytes(compress(b"id\tvalue\ny\t2\nx\t1\n"))
    assert table_profile(source) == table_profile(target)
    target.write_bytes(b"truncated archive")
    assert table_profile(target) is None
