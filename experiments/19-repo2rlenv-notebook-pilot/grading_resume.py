"""Reuse verified worker artifacts, never reuse their acceptance without execution."""

import json
from pathlib import Path

from grading_protocol import AlternativeSolution, Grader
from reference_replay import sha256


def load_resume(directory, context):
    directory = Path(directory)
    manifest = json.loads((directory / "artifact-manifest.json").read_text())
    if manifest.get("download_checked") is not True:
        raise ValueError("Resume requires a download-verified archive")
    records = {row["path"]: row for row in manifest["original_small_files"]}

    def read(name):
        path = directory / name
        record = records[name]
        if (
            path.is_symlink()
            or path.stat().st_size != record["bytes"]
            or sha256(path) != record["sha256"]
        ):
            raise ValueError("Resume evidence identity mismatch: " + name)
        return json.loads(path.read_text())

    result = read("result.json")
    if result.get("cleanup_verified") is not True:
        raise ValueError("Prior campaign cleanup must be verified")
    prior_context = read("grader/input.json")
    # Compare all current scientific inputs before reusing any worker program.
    # The later independent execution and its output path are added separately.
    prior_context = dict(prior_context)
    prior_context.pop("independent_solution", None)
    prior_context.pop("independent_execution", None)
    prior_context["paths"] = dict(prior_context["paths"])
    prior_context["paths"].pop("independent_outputs", None)
    if prior_context != context:
        raise ValueError("Resume scientific context differs from the current task")
    independent = AlternativeSolution.model_validate(read("independent-solution.json"))
    candidate = Grader.model_validate(read("candidate.json"))
    if independent.disposition != "ready" or candidate.disposition != "ready":
        raise ValueError("Resume requires submitted ready artifacts")
    return independent, candidate
