"""Reuse verified worker artifacts, never reuse their acceptance without execution."""

import json
from pathlib import Path

from grading_protocol import AlternativeSolution, Grader, Probes, check_probes
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


def load_saved_probes(directory, candidate):
    """Recover submitted probes from a hash-bound partial snapshot, not acceptance."""
    directory = Path(directory)
    records = {row["path"]: row for row in json.loads((directory / "manifest.json").read_text())}

    def read(name):
        path = directory / name
        record = records[name]
        if (
            path.is_symlink()
            or path.stat().st_size != record["bytes"]
            or sha256(path) != record["sha256"]
        ):
            raise ValueError("Probe recovery evidence identity mismatch: " + name)
        return json.loads(path.read_text())

    prior = Grader.model_validate(read("grading/candidate.json"))
    if prior != candidate:
        raise ValueError("Saved probes belong to a different grader contract")
    host = json.loads((directory / "host-stop.json").read_text())
    cleanup = json.loads((directory / "provider-cleanup.json").read_text())
    if (
        host.get("state") not in {"KILLED", "FAILED", "SUCCEEDED", "CANCELLED"}
        or cleanup.get("complete") is not True
        or cleanup.get("sandboxes") != []
    ):
        raise ValueError("Saved probe campaign requires verified resource teardown")
    suite = Probes.model_validate(read("grading/probes.json"))
    if suite.disposition != "ready":
        raise ValueError("Recovery requires a submitted ready probe suite")
    check_probes(suite, candidate)
    return suite
