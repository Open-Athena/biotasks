"""Representation parsing preserves values rather than deciding scientific rewards."""

import pytest

from biotasks.table_io import read_delimited_table


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_native_line_endings_and_quoted_fields(tmp_path, ending):
    path = tmp_path / "table.csv"
    raw = ending.join(["name,value", '"a,b",1.000', '"two\nlines",-0.0', ""])
    path.write_bytes(raw.encode())
    before = path.read_bytes()
    assert read_delimited_table(path) == (
        ["name", "value"],
        [["a,b", "1.000"], ["two\nlines", "-0.0"]],
    )
    assert path.read_bytes() == before


def test_empty_records_are_explicit_and_do_not_swallow_empty_fields(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text('id,value\n\na,1\n,\n"",2\n  ,3\n\n')
    with pytest.raises(ValueError, match="Empty CSV record"):
        read_delimited_table(path)
    assert read_delimited_table(path, allow_blank_records=True) == (
        ["id", "value"],
        [["a", "1"], ["", ""], ["", "2"], ["  ", "3"]],
    )


@pytest.mark.parametrize("text", ["id,value\na,1,extra\n", "id,value\na\n", 'id,value\n"oops\n'])
def test_extra_missing_or_malformed_values_cannot_disappear(tmp_path, text):
    path = tmp_path / "table.csv"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_delimited_table(path, allow_blank_records=True)


def test_bom_and_delimiter_require_the_declared_encoding_and_format(tmp_path):
    path = tmp_path / "table.tsv"
    path.write_bytes(b"\xef\xbb\xbfid\tvalue\na\t1\n")
    assert read_delimited_table(path, delimiter="\t")[0] == ["\ufeffid", "value"]
    assert read_delimited_table(path, delimiter="\t", encoding="utf-8-sig") == (
        ["id", "value"],
        [["a", "1"]],
    )


@pytest.mark.parametrize("text", ["", "\n\n"])
def test_absent_header_is_not_an_empty_success(tmp_path, text):
    path = tmp_path / "table.csv"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_delimited_table(path, allow_blank_records=True)
