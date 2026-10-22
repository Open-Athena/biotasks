"""Explicit per-release metadata; never reuse another notebook's attribution."""

import hashlib
import json
from pathlib import Path


def load_release_metadata(config):
    metadata = config.get("release_metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Explicit release_metadata is required")
    for key in ("repo_id", "title", "description", "methodology", "licenses_file", "seed_file"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"Explicit release metadata {key} is required")
    citations = metadata.get("citations")
    if (
        not isinstance(citations, list)
        or not citations
        or any(not isinstance(value, str) or not value.strip() for value in citations)
    ):
        raise ValueError("Explicit release citations are required")
    licenses = json.loads(Path(metadata["licenses_file"]).read_text())
    if not isinstance(licenses, dict) or not licenses:
        raise ValueError("Source-license evidence must be a nonempty object")
    source_license = licenses.get("notebook_license", {})
    if not isinstance(source_license, dict):
        raise ValueError("Source-license evidence must be an object")
    if "sha256" in source_license:
        text = source_license.get("text")
        if not isinstance(text, str):
            raise ValueError("Hashed source-license evidence needs text")
        text = text.encode()
        if hashlib.sha256(text).hexdigest() != source_license["sha256"]:
            raise ValueError("Source-license text differs from its recorded hash")
    seeds = json.loads(Path(metadata["seed_file"]).read_text())
    if not isinstance(seeds, list) or len(seeds) != 1:
        raise ValueError("A single explicitly selected release seed is required")
    provenance = seeds[0].get("provenance") if isinstance(seeds[0], dict) else None
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("Selected release seed needs provenance")
    if "source_provenance" in licenses and licenses["source_provenance"] != provenance:
        raise ValueError("Selected seed differs from the bundled source provenance")
    return metadata, licenses, provenance


def verify_bundle_licenses(task, licenses):
    recorded = json.loads((Path(task) / "environment/SOURCE-LICENSES.json").read_text())
    if recorded != licenses:
        raise ValueError("Release attribution differs from the validated task bundle")


def scientific_probe_documents(grading):
    """Publish the effective suite, preserving its original and repair evidence."""
    from grading_protocol import (
        Grader,
        GraderRepair,
        Probes,
        apply_probe_expectations,
        check_probes,
    )

    grading = Path(grading)

    def read(name):
        return json.loads((grading / name).read_text())

    original = Probes.model_validate(read("probes.json"))
    candidate = Grader.model_validate(read("final-candidate.json"))
    suite = original
    repair_path, revised_path = grading / "repair.json", grading / "repaired-probes.json"
    if repair_path.exists() != revised_path.exists():
        raise ValueError("Incomplete probe annotation repair evidence")
    repair = None
    if repair_path.exists():
        repair = GraderRepair.model_validate(read("repair.json"))
        expected_candidate, expected_suite = apply_probe_expectations(repair, original)
        suite = Probes.model_validate(read("repaired-probes.json"))
        if candidate != expected_candidate or suite != expected_suite:
            raise ValueError("Repaired probes or grader differ from recorded repair")
    check_probes(suite, candidate)
    expected = {p.name: p.model_dump() for p in suite.probes}
    seen = set()
    for control in read("final-controls.json"):
        if control["kind"] != "probe":
            continue
        probe = control.get("probe") or {}
        name = probe.get("name")
        if name in seen or name not in expected or probe != expected[name]:
            raise ValueError("Final controls do not match the effective probe suite")
        seen.add(name)
    if seen != set(expected):
        raise ValueError("Final controls omit an effective probe")
    documents = {"scientific-probes.json": suite.model_dump()}
    if repair is not None:
        documents["initial-scientific-probes.json"] = original.model_dump()
        documents["probe-expectation-corrections.json"] = {
            "corrections": [item.model_dump() for item in repair.probe_expectations],
            "mutation_scripts_unchanged": True,
        }
    return documents
