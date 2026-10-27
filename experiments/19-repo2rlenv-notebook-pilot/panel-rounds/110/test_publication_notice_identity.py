"""Publication must bind either recorded notice format without rewriting a task."""

import importlib.util
import sys
from pathlib import Path

import pytest

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
spec = importlib.util.spec_from_file_location(
    "snapshot_publication_operator", EXPERIMENT / "panel-rounds/109/prepare_snapshot_release.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FIRST = "a" * 64
SECOND = "b" * 64


@pytest.mark.parametrize(
    "notices",
    [
        {"notebook_source_sha256": FIRST},
        {"notebook": {"source_sha256": FIRST}},
        {"notebook_source_sha256": FIRST, "notebook": {"source_sha256": FIRST}},
    ],
)
def test_existing_notice_formats_return_the_same_identity(notices):
    assert module.notebook_notice_identity(notices) == FIRST


@pytest.mark.parametrize(
    "notices",
    [
        None,
        [],
        {},
        {"notebook": {}},
        {"notebook": FIRST},
        {"notebook_source_sha256": None},
        {"notebook_source_sha256": "a" * 63},
        {"notebook_source_sha256": "z" * 64},
        {"notebook": {"source_sha256": "unknown"}},
        {"notebook_source_sha256": FIRST, "notebook": {"source_sha256": SECOND}},
        {"notebook_source_sha256": FIRST, "notebook": {"source_sha256": None}},
    ],
)
def test_missing_malformed_or_conflicting_identities_are_refused(notices):
    with pytest.raises(ValueError):
        module.notebook_notice_identity(notices)
