"""Serialization observations must not become semantic acceptance."""

import hashlib

import pytest
from replay_tables import observe_tables, reviewable, table_profile


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


def test_unknown_differences_do_not_pass_gate():
    assert not reviewable({"all_outputs_byte_identical_to_original": False})
    assert reviewable(
        {
            "all_outputs_byte_identical_to_original": False,
            "all_output_differences_limited_to_table_serialization_or_row_order": True,
        }
    )
