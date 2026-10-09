import hashlib
import json

import pytest

from biotasks.notebook_seed import notebook_seed


def test_preserves_source_without_execution_outputs(tmp_path):
    path = tmp_path / "analysis.ipynb"
    raw = json.dumps(
        {
            "nbformat": 4,
            "metadata": {"private": "HIDDEN_METADATA"},
            "cells": [
                {"cell_type": "markdown", "source": ["Observed ", "data"]},
                {
                    "cell_type": "code",
                    "source": "analyze(data)",
                    "outputs": [{"text": "HIDDEN_OUTPUT"}],
                },
            ],
        }
    ).encode()
    path.write_bytes(raw)
    seed = notebook_seed(
        path,
        title="Example",
        source_url="https://example.org/notebook",
        revision="abc",
        license_id="MIT",
    )
    assert "Observed data" in seed["question_text"]
    assert "analyze(data)" in seed["question_text"]
    assert "HIDDEN" not in json.dumps(seed)
    assert seed["source_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("source", [None, [42], {"text": "not a cell"}])
def test_rejects_malformed_source(tmp_path, source):
    path = tmp_path / "bad.ipynb"
    path.write_text(
        json.dumps(
            {
                "nbformat": 4,
                "cells": [{"cell_type": "code", "source": source}],
            }
        )
    )
    with pytest.raises(ValueError, match="Invalid source"):
        notebook_seed(path, title="Bad", source_url="url", revision="abc", license_id="MIT")
