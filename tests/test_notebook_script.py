"""Admission and executable-coverage regression cases, without notebook execution."""

import ast
import json
import os

import pytest

from biotasks.notebook_script import UnsupportedNotebook, export_python


def source(tmp_path, cells, **metadata):
    path = tmp_path / "source.ipynb"
    path.write_text(
        json.dumps(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "metadata": {"language_info": {"name": "python"}, **metadata},
                "cells": [dict(cell_type="code", source=text, metadata={}) for text in cells],
            }
        )
    )
    return path


def test_export_preserves_order_and_has_no_kernel_or_markers(tmp_path):
    path = source(tmp_path, ["x = [1, 2]\nx.append(3)", "result = sum(x)"])
    script, receipt = export_python(path)
    assert ast.dump(ast.parse(script)) == ast.dump(ast.parse("x=[1,2]\nx.append(3)\nresult=sum(x)"))
    assert "# %%" not in script and "get_ipython" not in script
    assert receipt["code_cells"] == 2
    assert receipt["executed"] is False
    assert export_python(path) == (script, receipt)


@pytest.mark.parametrize(
    "code",
    [
        "%matplotlib widget",
        "%%timeit\nx = 1",
        "%%time -n 2\nx = 1",
        "%time x = 1",
        "%matplotlib inline; x = 1",
        "!curl example.com",
        "await f()",
        "get_ipython().run_line_magic('time', 'f()')",
    ],
)
def test_kernel_execution_features_rejected(tmp_path, code):
    with pytest.raises(UnsupportedNotebook):
        export_python(source(tmp_path, [code]))


def test_supported_presentation_wrappers_preserve_single_execution(tmp_path):
    path = source(
        tmp_path,
        ["%matplotlib inline\nvalues = []", "%%time\nvalues.append(7)", "result = sum(values)"],
        celltoolbar="Raw Cell Format",
        vscode={"interpreter": {"hash": "editor-only"}},
    )
    script, receipt = export_python(path)
    assert ast.dump(ast.parse(script)) == ast.dump(
        ast.parse("values=[]\nvalues.append(7)\nresult=sum(values)")
    )
    scope = {}
    exec(compile(script, "synthetic.py", "exec"), scope)
    assert scope["values"] == [7] and scope["result"] == 7
    assert receipt["presentation_normalizations"] == [
        {"cell_index": 0, "line": 1, "directive": "%matplotlib inline"},
        {"cell_index": 1, "line": 1, "directive": "%%time"},
    ]
    assert receipt["ignored_editor_metadata"]["celltoolbar"] == "Raw Cell Format"
    assert export_python(path) == (script, receipt)


def test_magic_text_in_strings_comments_and_modulo_is_preserved(tmp_path):
    code = 'text = """\n%matplotlib inline\n%%time\n"""\n# %%time\nvalue = (7\n% 3)'
    script, receipt = export_python(source(tmp_path, [code]))
    assert ast.dump(ast.parse(script)) == ast.dump(ast.parse(code))
    assert receipt["presentation_normalizations"] == []


def test_cell_timing_wrapper_cannot_appear_after_python_statements(tmp_path):
    with pytest.raises(UnsupportedNotebook):
        export_python(source(tmp_path, ["x = 1\n%%time\nx += 1"]))


def test_metadata_cannot_silently_skip_analysis(tmp_path):
    path = source(tmp_path, ["raise RuntimeError('do not run')"])
    data = json.loads(path.read_text())
    data["cells"][0]["metadata"]["tags"] = ["skip-execution"]
    path.write_text(json.dumps(data))
    with pytest.raises(UnsupportedNotebook, match="execution directives"):
        export_python(path)


@pytest.mark.parametrize("editable,deletable", [(True, True), (False, False)])
def test_cell_editing_permissions_do_not_skip_or_change_code(tmp_path, editable, deletable):
    path = source(tmp_path, ["result = 1 + 2"])
    data = json.loads(path.read_text())
    metadata = {"editable": editable, "deletable": deletable}
    data["cells"][0]["metadata"] = metadata
    path.write_text(json.dumps(data))
    script, receipt = export_python(path)
    assert ast.dump(ast.parse(script)) == ast.dump(ast.parse("result = 1 + 2"))
    assert receipt["ignored_cell_editor_metadata"] == [{"cell_index": 0, "metadata": metadata}]
    assert export_python(path) == (script, receipt)


@pytest.mark.parametrize("value", ["false", 0, None, {"skip": True}])
def test_invalid_editor_permissions_are_rejected(tmp_path, value):
    path = source(tmp_path, ["result = 3"])
    data = json.loads(path.read_text())
    data["cells"][0]["metadata"] = {"editable": value}
    path.write_text(json.dumps(data))
    with pytest.raises(UnsupportedNotebook, match="editor metadata"):
        export_python(path)


def test_docs_execution_policy_is_recorded_not_used_to_skip(tmp_path):
    path = source(
        tmp_path,
        ["raise RuntimeError('conversion must never execute')"],
        mystnb={"execution_mode": "off"},
    )
    script, receipt = export_python(path)
    assert "raise RuntimeError" in script
    assert receipt["documentation_execution_policy"] == {"execution_mode": "off"}


def test_exporter_omission_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("jupytext.writes", lambda *a, **kw: "x = 1\n")
    with pytest.raises(UnsupportedNotebook, match="omitted"):
        export_python(source(tmp_path, ["x=1", "endpoint=x+1"]))


def test_markdown_stays_in_order_as_comments_without_changing_execution(tmp_path):
    path = source(tmp_path, ["from __future__ import annotations\nx = 1", "result = x + 1"])
    notebook = json.loads(path.read_text())
    notebook["cells"].insert(
        0, dict(cell_type="markdown", source="# Analysis\nExplain inputs.", metadata={})
    )
    notebook["cells"].insert(
        2,
        dict(
            cell_type="markdown",
            source='```python\nraise RuntimeError("narrative only")\n```\n%not_a_magic',
            metadata={},
        ),
    )
    notebook["cells"].append(
        dict(cell_type="raw", source="raise RuntimeError('raw only')", metadata={})
    )
    notebook["cells"][1]["outputs"] = [
        {"output_type": "stream", "name": "stdout", "text": "saved-output-only"}
    ]
    path.write_text(json.dumps(notebook))
    script, receipt = export_python(path)
    assert script.index("# Analysis") < script.index("from __future__")
    assert script.index("x = 1") < script.index("narrative only") < script.index("result =")
    assert "raw only" not in script and "saved-output-only" not in script
    assert ast.dump(ast.parse(script)) == ast.dump(
        ast.parse("from __future__ import annotations\nx = 1\nresult = x + 1")
    )
    assert receipt["markdown_cells"] == 2
    assert receipt["markdown_representation"] == "line_comments"
    assert export_python(path) == (script, receipt)


def test_unsupported_language_is_not_misclassified_as_broken_source(tmp_path):
    with pytest.raises(UnsupportedNotebook, match="Python language"):
        export_python(source(tmp_path, ["x <- 1"], language_info={"name": "R"}))


def test_pairing_formats_are_recorded_without_controlling_conversion(tmp_path):
    pairing = {"formats": "ipynb,md:myst,py:percent"}
    path = source(tmp_path, ["raise RuntimeError('do not execute')"], jupytext=pairing)
    script, receipt = export_python(path)
    assert ast.dump(ast.parse(script)) == ast.dump(
        ast.parse("raise RuntimeError('do not execute')")
    )
    assert receipt["source_pairing_metadata"] == pairing
    assert receipt["format"] == "py:nomarker"
    assert "# %%" not in script


@pytest.mark.parametrize("pairing", [{"formats": []}, {"unknown_option": True}, "py"])
def test_unknown_or_malformed_pairing_options_are_rejected(tmp_path, pairing):
    with pytest.raises(UnsupportedNotebook, match="Jupytext metadata"):
        export_python(source(tmp_path, ["x=1"], jupytext=pairing))


def test_literal_directory_changes_preserve_position_without_running_at_conversion(
    tmp_path, monkeypatch
):
    directory = tmp_path / "data set"
    directory.mkdir()
    (directory / "value.txt").write_text("observed")
    path = source(
        tmp_path,
        [
            "os = 'analysis value'\nvalues = []",
            "%cd 'data set'\nvalues.append(open('value.txt').read())",
            "%cd ..\nresult = os",
        ],
    )
    monkeypatch.chdir(tmp_path)
    with monkeypatch.context() as patch:

        def no_directory_changes(*args):
            raise AssertionError("Conversion must not change directories")

        patch.setattr(os, "chdir", no_directory_changes)
        script, receipt = export_python(path)
        assert export_python(path) == (script, receipt)
    scope = {}
    exec(compile(script, "synthetic.py", "exec"), scope)
    assert scope["values"] == ["observed"]
    assert scope["result"] == "analysis value"
    assert os.getcwd() == str(tmp_path)
    assert [change["path"] for change in receipt["directory_normalizations"]] == ["data set", ".."]
    assert receipt["executed"] is False


@pytest.mark.parametrize("argument", ["example3", "./data", "../data", "/tmp/data", '"data set"'])
def test_supported_literal_directory_paths(tmp_path, argument):
    script, receipt = export_python(source(tmp_path, [f"%cd {argument}\nresult = 1"]))
    assert ".chdir(" in script
    assert len(receipt["directory_normalizations"]) == 1


@pytest.mark.parametrize(
    "argument",
    [
        "",
        "-",
        "-q data",
        "-2",
        "-- data",
        "$DATA",
        "{data}",
        "~",
        "data*",
        "a b",
        "'a' 'b'",
        "'a",
        "a; print(1)",
        "data # comment",
        "'a\\b'",
    ],
)
def test_directory_expansion_options_and_ambiguous_arguments_are_rejected(tmp_path, argument):
    with pytest.raises(UnsupportedNotebook):
        export_python(source(tmp_path, [f"%cd {argument}"]))


@pytest.mark.parametrize("cell", ["__import__ = other", "def f(__import__): pass"])
@pytest.mark.parametrize("before", [True, False])
def test_directory_changes_reject_shadowed_import_builtin_in_any_cell(tmp_path, cell, before):
    cells = [cell, "%cd data"] if before else ["%cd data", cell]
    with pytest.raises(UnsupportedNotebook, match="unshadowed"):
        export_python(source(tmp_path, cells))


def test_directory_magic_in_strings_and_modulo_are_not_rewritten(tmp_path):
    code = 'text = """\n%cd data\n__import__\n"""\n# %cd data\nvalue = (7\n% 3)'
    script, receipt = export_python(source(tmp_path, [code]))
    assert ast.dump(ast.parse(script)) == ast.dump(ast.parse(code))
    assert receipt["directory_normalizations"] == []


@pytest.mark.parametrize("prefix", ["value = (7\n", "value = 7 \\\n"])
@pytest.mark.parametrize("directive", ["%matplotlib inline", "%cd data"])
def test_continued_statement_cannot_be_misclassified_as_directive(tmp_path, prefix, directive):
    with pytest.raises(UnsupportedNotebook):
        export_python(source(tmp_path, [prefix + directive + "\n)"]))


def test_directory_history_is_not_silently_recreated(tmp_path):
    with pytest.raises(UnsupportedNotebook, match="kernel state"):
        export_python(source(tmp_path, ["%cd data\nresult = _dh"]))


@pytest.mark.parametrize("tags", [[], ["remove-input"]])
def test_presentation_tags_retain_execution(tmp_path, tags):
    path = source(tmp_path, ["values = []", "values.append(7)"])
    notebook = json.loads(path.read_text())
    notebook["cells"][1]["metadata"]["tags"] = tags
    path.write_text(json.dumps(notebook))
    script, receipt = export_python(path)
    scope = {}
    exec(compile(script, "synthetic.py", "exec"), scope)
    assert scope["values"] == [7]
    assert receipt["ignored_presentation_tags"] == [{"cell_index": 1, "tags": tags}]
    assert ast.dump(ast.parse(script)) == ast.dump(ast.parse("values=[]\nvalues.append(7)"))


@pytest.mark.parametrize(
    "tags", [None, "remove-input", [0], ["remove-input", "skip-execution"], ["remove-cell"]]
)
def test_unknown_or_malformed_tags_remain_unsupported(tmp_path, tags):
    path = source(tmp_path, ["result = 1"])
    notebook = json.loads(path.read_text())
    notebook["cells"][0]["metadata"]["tags"] = tags
    path.write_text(json.dumps(notebook))
    with pytest.raises(UnsupportedNotebook, match="execution directives"):
        export_python(path)
