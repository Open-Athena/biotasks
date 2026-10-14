"""Admission and executable-coverage regression cases, without notebook execution."""

import ast
import json

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
        "%matplotlib inline",
        "!curl example.com",
        "await f()",
        "get_ipython().run_line_magic('time', 'f()')",
    ],
)
def test_kernel_execution_features_rejected(tmp_path, code):
    with pytest.raises(UnsupportedNotebook):
        export_python(source(tmp_path, [code]))


def test_metadata_cannot_silently_skip_analysis(tmp_path):
    path = source(tmp_path, ["raise RuntimeError('do not run')"])
    data = json.loads(path.read_text())
    data["cells"][0]["metadata"]["tags"] = ["skip-execution"]
    path.write_text(json.dumps(data))
    with pytest.raises(UnsupportedNotebook, match="execution directives"):
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
