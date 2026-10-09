import hashlib
import json
from pathlib import Path

import pytest

from biotasks.notebook_pipeline import prepare, source_text


def test_notebook_outputs_are_not_authoring_inputs():
    raw = json.dumps(
        {
            "nbformat": 4,
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["x = 1\n", "print(x)"],
                    "outputs": [{"text": "SECRET_REFERENCE"}],
                    "metadata": {"secret": "metadata"},
                },
                {"cell_type": "markdown", "source": "A biological question"},
            ],
        }
    ).encode()
    text = source_text(raw, ".ipynb")
    assert "print(x)" in text
    assert "A biological question" in text
    assert "SECRET_REFERENCE" not in text
    assert "metadata" not in text


def inputs(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()
    digest = hashlib.sha256(b"# Analysis\n").hexdigest()
    (cache / digest).write_bytes(b"# Analysis\n")
    manifest = tmp_path / "seeds.json"
    manifest.write_text(
        json.dumps(
            {
                "seeds": [
                    {
                        "id": "one",
                        "domain": "biology",
                        "url": "https://example.org/seed",
                        "path": "vignette.Rmd",
                        "source_sha256": digest,
                    },
                    {
                        "id": "two",
                        "domain": "biology",
                        "url": "https://example.org/missing",
                        "path": "vignette.Rmd",
                        "source_sha256": "0" * 64,
                    },
                ]
            }
        )
    )
    protocol = tmp_path / "protocol.json"
    protocol.write_text('{"solver_timeout_seconds": 300}')
    return manifest, protocol, cache


def test_missing_source_preserves_panel_and_no_overwrite(tmp_path):
    manifest, protocol, cache = inputs(tmp_path)
    output = tmp_path / "run"
    result = prepare(manifest, protocol, cache, output)
    assert [s["status"] for s in result["seeds"]] == ["authoring_prepared", "intake_failed"]
    assert result["model_calls"] == 0
    assert all(s["tasks"] == s["attempts"] == [] for s in result["seeds"])
    assert (output / "one/seed.txt").read_text() == "# Analysis\n"
    with pytest.raises(FileExistsError):
        prepare(manifest, protocol, cache, output)


def test_hash_mismatch_prevents_workspace_creation(tmp_path):
    manifest, protocol, cache = inputs(tmp_path)
    next(cache.iterdir()).write_bytes(b"changed source")
    result = prepare(manifest, protocol, cache, tmp_path / "run")
    assert result["seeds"][0]["error"] == "Source SHA-256 mismatch"
    assert not (tmp_path / "run/one").exists()


def test_path_traversal_rejected_before_output_created(tmp_path):
    manifest, protocol, cache = inputs(tmp_path)
    panel = json.loads(manifest.read_text())
    panel["seeds"][0]["id"] = "../outside"
    manifest.write_text(json.dumps(panel))
    with pytest.raises(ValueError, match="safe identifiers"):
        prepare(manifest, protocol, cache, tmp_path / "run")
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize(
    "notebook", [[], {"nbformat": 4, "cells": None}, {"nbformat": 4, "cells": [None]}]
)
def test_malformed_notebooks_are_intake_errors(notebook):
    with pytest.raises(ValueError):
        source_text(json.dumps(notebook).encode(), ".ipynb")
