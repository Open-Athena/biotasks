"""Offline source intake for the notebook task experiment; never executes seed code."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from biotasks.prompts import load_prompt

MAX_SOURCE_BYTES = 16 * 1024 * 1024


def source_text(raw: bytes, suffix: str) -> str:
    """Retain notebook code/narrative but omit outputs, attachments and metadata."""
    text = raw.decode("utf-8")
    if suffix == ".Rmd":
        return text
    if suffix != ".ipynb":
        raise ValueError(f"Unsupported seed format: {suffix}")
    notebook = json.loads(text)
    if not isinstance(notebook, dict) or notebook.get("nbformat") != 4:
        raise ValueError("Only notebook format 4 is supported")
    if not isinstance(notebook.get("cells"), list):
        raise ValueError("Notebook cells must be a list")
    sections = []
    for cell in notebook["cells"]:
        if not isinstance(cell, dict) or cell.get("cell_type") not in {"code", "markdown", "raw"}:
            raise ValueError("Unknown notebook cell type")
        source = cell["source"]
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = "".join(source)
        if not isinstance(source, str):
            raise ValueError("Cell source must be text")
        sections.append(f"--- {cell['cell_type']} cell ---\n{source}")
    return "\n\n".join(sections) + "\n"


def prepare(manifest: Path, protocol: Path, cache: Path, output: Path) -> dict:
    """Verify hash-addressed local inputs and prepare fresh authoring workspaces.

    Cache names are source SHA-256 values. Missing/mismatched sources are recorded
    individually; the panel denominator is never reduced by intake failures.
    Output must not exist, so earlier evidence cannot be overwritten.
    """
    panel = json.loads(manifest.read_text())
    settings = json.loads(protocol.read_text())
    ids = [seed["id"] for seed in panel["seeds"]]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[a-z0-9-]+", i) for i in ids):
        raise ValueError("Seed IDs must be unique, safe identifiers")
    for seed in panel["seeds"]:
        if not re.fullmatch(r"[0-9a-f]{64}", seed["source_sha256"]):
            raise ValueError("Invalid source SHA-256")
    prompt = load_prompt("notebook-task-v1")
    worker_prompts = {
        stage: load_prompt(name)
        for stage, name in {
            "review": "notebook-review-v1",
            "repair": "notebook-repair-v1",
        }.items()
    }
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for seed in panel["seeds"]:
        row = {
            "id": seed["id"],
            "domain": seed["domain"],
            "source_url": seed["url"],
            "source_sha256": seed["source_sha256"],
            "status": "intake_failed",
            "tasks": [],
            "attempts": [],
        }
        try:
            with (cache / seed["source_sha256"]).open("rb") as source:
                raw = source.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ValueError("Source exceeds intake size limit")
            if hashlib.sha256(raw).hexdigest() != seed["source_sha256"]:
                raise ValueError("Source SHA-256 mismatch")
            text = source_text(raw, Path(seed["path"]).suffix)
        except (OSError, ValueError, KeyError, TypeError) as error:
            row["error"] = str(error)
        else:
            workspace = output / seed["id"]
            workspace.mkdir()
            (workspace / "seed.txt").write_text(text)
            (workspace / "seed.json").write_text(json.dumps(seed, indent=2) + "\n")
            (workspace / "protocol.json").write_text(json.dumps(settings, indent=2) + "\n")
            (workspace / "prompt.md").write_text(prompt)
            for stage, stage_prompt in worker_prompts.items():
                (workspace / f"{stage}-prompt.md").write_text(stage_prompt)
            row.update(
                status="authoring_prepared",
                source_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                worker_prompt_sha256={
                    stage: hashlib.sha256(value.encode()).hexdigest()
                    for stage, value in worker_prompts.items()
                },
            )
        records.append(row)
    result = {
        "schema_version": 1,
        "stage": "source_intake",
        "model_calls": 0,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "seeds": records,
    }
    (output / "intake.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.manifest, args.protocol, args.cache, args.output)
    counts = {
        status: sum(s["status"] == status for s in result["seeds"])
        for status in ("authoring_prepared", "intake_failed")
    }
    print(json.dumps(counts))
    if counts["intake_failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
