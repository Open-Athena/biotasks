"""Capture generic parsing support; never author scientific comparison rules."""

import hashlib
import json
from importlib.resources import files
from pathlib import Path

MODULE = "biotasks_table_io.py"
MANIFEST = "parsing-support.json"


def load_support(root, expected=None):
    root = Path(root)
    source, receipt = root / MODULE, root / MANIFEST
    if root.is_symlink() or source.is_symlink() or receipt.is_symlink():
        raise ValueError("Parsing support cannot use symbolic links")
    if not source.exists() and not receipt.exists() and expected is None:
        return None  # Historical graders did not have the optional support.
    if source.is_symlink() or receipt.is_symlink() or not source.is_file() or not receipt.is_file():
        raise ValueError("Parsing support needs its original regular source and manifest")
    raw = source.read_bytes()
    metadata = json.loads(receipt.read_text())
    if metadata != {
        "schema": "delimited-table-reader-v1",
        "module": MODULE,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    } or (expected is not None and metadata != expected):
        raise ValueError("Parsing support differs from its captured identity")
    return metadata


def capture_support(root):
    root = Path(root)
    if root.is_symlink() or (root / MODULE).is_symlink() or (root / MANIFEST).is_symlink():
        raise ValueError("Parsing support cannot use symbolic links")
    root.mkdir(parents=True, exist_ok=True)
    raw = files("biotasks").joinpath("table_io.py").read_bytes()
    expected = {
        "schema": "delimited-table-reader-v1",
        "module": MODULE,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    if (root / MODULE).exists() or (root / MANIFEST).exists():
        return load_support(root, expected)
    (root / MODULE).write_bytes(raw)
    (root / MANIFEST).write_text(json.dumps(expected, indent=2) + "\n")
    return expected


def support_interface(root):
    metadata = load_support(root)
    assert metadata is not None
    return {
        **metadata,
        "import": "from biotasks_table_io import read_delimited_table",
        "authoring_source": "/work/biotasks_table_io.py",
        "authoring_import": "Use PYTHONPATH=/work for a focused shell check. The controller places this same module beside grade.py in controls and Harbor.",
        "scope": "Optional syntax reader only. The worker owns scientific comparisons and must publicly declare any enabled representation normalization.",
        "source": (Path(root) / MODULE).read_text(),
    }
