"""Capture generic parsing support; never author scientific comparison rules."""

import hashlib
import json
from importlib.resources import files
from pathlib import Path

MODULE = "biotasks_table_io.py"
MANIFEST = "parsing-support.json"
NOTICE = "LICENSE.biotasks"


def identity(raw, notice):
    return {
        "schema": "delimited-table-reader-v1",
        "module": MODULE,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "license": {
            "path": NOTICE,
            "spdx": "Apache-2.0",
            "sha256": hashlib.sha256(notice).hexdigest(),
            "bytes": len(notice),
        },
    }


def load_support(root, expected=None):
    root = Path(root)
    source, receipt = root / MODULE, root / MANIFEST
    notice = root / NOTICE
    if root.is_symlink() or any(p.is_symlink() for p in (source, receipt, notice)):
        raise ValueError("Parsing support cannot use symbolic links")
    if not any(p.exists() for p in (source, receipt, notice)) and expected is None:
        return None  # Historical graders did not have the optional support.
    if not all(p.is_file() for p in (source, receipt, notice)):
        raise ValueError("Parsing support needs its original regular source and manifest")
    raw = source.read_bytes()
    metadata = json.loads(receipt.read_text())
    if metadata != identity(raw, notice.read_bytes()) or (
        expected is not None and metadata != expected
    ):
        raise ValueError("Parsing support differs from its captured identity")
    return metadata


def capture_support(root):
    root = Path(root)
    if root.is_symlink() or any((root / name).is_symlink() for name in (MODULE, MANIFEST, NOTICE)):
        raise ValueError("Parsing support cannot use symbolic links")
    root.mkdir(parents=True, exist_ok=True)
    raw = files("biotasks").joinpath("table_io.py").read_bytes()
    # The research runner always has its frozen source checkout. LICENSE is an
    # explicit source_archive root file; no current-working-directory lookup.
    notice = (Path(__file__).resolve().parents[2] / "LICENSE").read_bytes()
    expected = identity(raw, notice)
    if any((root / name).exists() for name in (MODULE, MANIFEST, NOTICE)):
        return load_support(root, expected)
    (root / MODULE).write_bytes(raw)
    (root / NOTICE).write_bytes(notice)
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
