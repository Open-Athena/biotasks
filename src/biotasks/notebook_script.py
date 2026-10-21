"""Conservative, deterministic notebook export; never execute source code.

The first admission profile covers ordinary Python in nbformat 4. Other
languages and execution features require their own verified export profiles.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import tokenize
from importlib.metadata import version
from pathlib import Path

import jupytext

MAX_SOURCE_BYTES = 16 * 1024 * 1024
PROFILE = "python-narrative-v3"


class UnsupportedNotebook(ValueError):
    """Conversion is unsupported; this does not diagnose broken science."""


def _text(value: str | list[str]) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(line, str) for line in value):
        return "".join(value)
    raise UnsupportedNotebook("Cell source must be text")


def _python_tree(source: str) -> ast.Module:
    try:
        tree = ast.parse(source)
        # ast.parse alone accepts top-level await and misplaced future imports.
        compile(tree, "analysis.py", "exec")
    except (SyntaxError, ValueError) as error:
        raise UnsupportedNotebook(
            "Source requires unsupported Python execution semantics"
        ) from error
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {"get_ipython", "In", "Out"}:
            raise UnsupportedNotebook("Interactive kernel state is outside this conversion profile")
    return tree


def _presentation_directives(source: str, cell: int) -> tuple[str, list[dict]]:
    """Remove only explicitly supported display/timing wrappers, never strings.

    Token positions distinguish a real directive from the same text inside a
    multiline string. Timing repetitions, shell commands and other magics remain
    unsupported; no notebook code is evaluated during conversion.
    """
    lines = source.splitlines(keepends=True)
    changes = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as error:
        raise UnsupportedNotebook("Cannot tokenize notebook code") from error
    directive_lines = {
        token.start[0]
        for token in tokens
        if token.type == tokenize.OP and token.string == "%" and token.start[1] == 0
    }
    for number in sorted(directive_lines):
        line = lines[number - 1].rstrip("\r\n")
        words = line.split()
        if words == ["%matplotlib", "inline"] or (number == 1 and words == ["%%time"]):
            changes.append({"cell_index": cell, "line": number, "directive": line})
            lines[number - 1] = "# Notebook presentation directive: " + line + "\n"
    return "".join(lines), changes


def export_python(path: Path) -> tuple[str, dict]:
    """Export with Jupytext, then compare the ordered executable syntax trees.

    Presentation metadata and stored outputs never control this fresh script
    run. Execution directives and unknown code-cell metadata fail closed.
    The original notebook remains the provenance artifact.
    """
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise UnsupportedNotebook("Source exceeds the bounded intake size")
    raw = path.read_bytes()
    notebook = json.loads(raw)
    if notebook.get("nbformat") != 4:
        raise UnsupportedNotebook("Only nbformat 4 is supported")
    metadata = notebook.get("metadata", {})
    languages = {
        str(value).lower()
        for value in (
            metadata.get("kernelspec", {}).get("language"),
            metadata.get("language_info", {}).get("name"),
        )
        if value
    }
    if languages != {"python"}:
        raise UnsupportedNotebook("This profile requires an unambiguous Python language")
    allowed_metadata = {
        "kernelspec",
        "language_info",
        "widgets",
        "mystnb",
        "toc",
        "jupytext",
        "celltoolbar",
        "vscode",
    }
    if set(metadata) - allowed_metadata:
        raise UnsupportedNotebook("Notebook metadata needs a supported conversion profile")
    # File-pairing formats describe documentation synchronization, not code.
    # Do not pass source Jupytext options to the exporter: its conversion
    # policy remains explicit below, and unknown options still fail closed.
    pairing = metadata.get("jupytext", {})
    if (
        not isinstance(pairing, dict)
        or set(pairing) - {"formats"}
        or ("formats" in pairing and not isinstance(pairing["formats"], str))
    ):
        raise UnsupportedNotebook("Jupytext metadata needs a supported conversion profile")
    # MyST's build-time execution switch does not change the notebook program.
    # Preserve and explicitly record it, rather than adopting it as a skip rule.
    myst = metadata.get("mystnb", {})
    if set(myst) - {"execution_mode"} or myst.get("execution_mode") not in {
        None,
        "off",
        "auto",
        "force",
        "cache",
        "inline",
    }:
        raise UnsupportedNotebook("Unsupported documentation execution directives")
    code: list[str] = []
    cells: list[dict] = []
    markdown_count = 0
    normalizations = []
    for cell_index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") not in {"code", "markdown", "raw"}:
            raise UnsupportedNotebook("Unknown cell type")
        if cell["cell_type"] == "raw":
            continue
        text = _text(cell["source"])
        if cell["cell_type"] == "markdown":
            cells.append(
                dict(cell_type="markdown", source=text, metadata={}, id=f"source-{len(cells)}")
            )
            markdown_count += 1
            continue
        cell_metadata = cell.get("metadata", {})
        if set(cell_metadata) - {"collapsed", "scrolled", "trusted", "execution"}:
            raise UnsupportedNotebook("Code-cell execution directives are unsupported")
        text, changes = _presentation_directives(text, cell_index)
        normalizations.extend(changes)
        code.append(text)
        cells.append(
            dict(
                cell_type="code",
                source=text,
                metadata={},
                execution_count=None,
                outputs=[],
                id=f"source-{len(cells)}",
            )
        )
    if not code:
        raise UnsupportedNotebook("No executable cells")
    baseline_tree = _python_tree("\n\n".join(code) + "\n")
    # Retain narrative in place as line comments. Raw cells, stored outputs and
    # formatting directives must not become executable statements.
    converted = jupytext.writes(
        jupytext.reads(
            json.dumps(
                {
                    "nbformat": 4,
                    "nbformat_minor": 5,
                    "metadata": {
                        "kernelspec": metadata.get("kernelspec", {}),
                        "language_info": metadata.get("language_info", {}),
                    },
                    "cells": cells,
                }
            ),
            fmt="ipynb",
        ),
        fmt="py:nomarker",
        notebook_metadata_filter="-all",
        cell_metadata_filter="-all",
    )
    converted_tree = _python_tree(converted)
    syntax = ast.dump(baseline_tree, include_attributes=False)
    if syntax != ast.dump(converted_tree, include_attributes=False):
        raise UnsupportedNotebook("Exporter changed or omitted executable statements")
    receipt = {
        "profile": PROFILE,
        "converter": "jupytext",
        "converter_version": version("jupytext"),
        "format": "py:nomarker",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "script_sha256": hashlib.sha256(converted.encode()).hexdigest(),
        "executable_ast_sha256": hashlib.sha256(syntax.encode()).hexdigest(),
        "code_cells": len(code),
        "markdown_cells": markdown_count,
        "markdown_representation": "line_comments",
        "ordered_code_equivalence": True,
        "equivalence_basis": "Python statements after recorded presentation normalization",
        "presentation_normalizations": normalizations,
        "ignored_editor_metadata": {
            key: metadata[key] for key in ("celltoolbar", "vscode") if key in metadata
        },
        "documentation_execution_policy": myst,
        "stored_outputs_used_as_evidence": False,
        "executed": False,
    }
    if pairing:
        receipt["source_pairing_metadata"] = pairing
    return converted, receipt
