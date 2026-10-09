"""Convert a Jupyter notebook into source material for SETA Seed2Synth.

This intake preserves markdown and code, not outputs or hidden notebook metadata.
It does not choose an analysis, generate a task, or establish scientific fidelity.
"""

import hashlib
import json
from pathlib import Path


def notebook_seed(
    path: Path, *, title: str, source_url: str, revision: str, license_id: str
) -> dict[str, str]:
    """Return the upstream seed fields and a reproducible source identity."""
    if not all((title.strip(), source_url.strip(), revision.strip(), license_id.strip())):
        raise ValueError("Title, source URL, revision and source license are required")
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Notebook exceeds the 16 MiB intake limit")
    raw = path.read_bytes()
    notebook = json.loads(raw)
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError("Expected a version 4 Jupyter notebook")
    sections = []
    for index, cell in enumerate(notebook["cells"]):
        kind = cell.get("cell_type")
        if kind not in {"markdown", "code", "raw"}:
            raise ValueError(f"Unsupported cell type at cell {index}")
        source = cell.get("source")
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = "".join(source)
        if not isinstance(source, str):
            raise ValueError(f"Invalid source at cell {index}")
        if source.strip():
            sections.append(f"--- {kind} cell {index} ---\n{source}")
    if not sections:
        raise ValueError("Notebook contains no source text")
    text = "\n\n".join(sections)
    if len(text.encode()) > 512 * 1024:
        raise ValueError("Notebook source exceeds the 512 KiB intake limit; no silent truncation")
    return {
        "source": source_url,
        "url": source_url,
        "title": title,
        "question_text": text,
        "license": license_id,
        "source_revision": revision,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }
