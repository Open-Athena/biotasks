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


def release_execution_provenance(config, validation):
    """Bind an unattended label to this source's archived pipeline and native result."""
    pipeline_path = config.get("autonomous_pipeline")
    manifest_path = config.get("autonomous_archive_manifest")
    if pipeline_path is None and manifest_path is None:
        return "assisted", {}
    if not pipeline_path or not manifest_path or validation.get("accepted") is not True:
        raise ValueError("Unattended provenance needs accepted, archived execution evidence")
    pipeline_path, manifest_path = Path(pipeline_path), Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("download_checked") is not True:
        raise ValueError("Unattended archive must have verified export readback")
    rows = {row["path"]: row for row in manifest["files"]}
    if len(rows) != len(manifest["files"]):
        raise ValueError("Ambiguous unattended archive paths")

    def archived(path):
        path = Path(path)
        relative = path.resolve().relative_to(manifest_path.resolve().parent).as_posix()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        row = rows.get(relative)
        if row is None or row["sha256"] != digest or row["bytes"] != len(raw):
            raise ValueError("Unattended execution differs from its archive")
        return json.loads(raw), digest

    pipeline, pipeline_hash = archived(pipeline_path)
    native, native_hash = archived(Path(config["native"]) / "result.json")
    seeds = json.loads(Path(config["release_metadata"]["seed_file"]).read_text())
    if len(seeds) != 1 or pipeline.get("source") != seeds[0]:
        raise ValueError("Unattended execution belongs to a different release source")
    stages = pipeline.get("stages", [])
    if (
        pipeline.get("status") != "validated"
        or pipeline.get("autonomous") is not True
        or type(pipeline.get("operator_interventions")) is not int
        or pipeline["operator_interventions"] != 0
        or [stage.get("name") for stage in stages]
        != ["preparation", "setup", "replay", "specification", "construction", "grading", "native"]
        or any(stage.get("status") != "completed" for stage in stages)
        or native.get("status") != "native_validated_solver_attempt_recorded"
        or native.get("publication_ready") is not True
    ):
        raise ValueError("Execution does not establish a completed unattended pipeline")
    return "unattended", {
        "autonomous-execution.json": {
            "pipeline_sha256": pipeline_hash,
            "native_result_sha256": native_hash,
            "archive_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "source_sha256": seeds[0]["source_sha256"],
            "factory_revision": pipeline["factory_revision"],
            "bundle_hash": validation["bundle_hash"],
            "operator_interventions": 0,
            "stages": [{"name": stage["name"], "status": stage["status"]} for stage in stages],
            "reasoning_effort_requested": pipeline.get("reasoning_effort_requested"),
            "served_endpoint_effective_effort_verified": pipeline.get(
                "served_endpoint_effective_effort_verified", False
            ),
        }
    }


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
        if repair.probe_concerns is not None:
            documents["probe-expectation-corrections.json"]["suite_concerns"] = {
                "original": original.concerns,
                "revised": suite.concerns,
            }
    return documents
