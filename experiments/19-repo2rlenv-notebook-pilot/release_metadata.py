"""Explicit per-release metadata; never reuse another notebook's attribution."""

import hashlib
import json
import re
from pathlib import Path


def additional_release_evidence(config, *, reserved):
    """Attach reviewed, hash-pinned publication notices outside the tested task."""
    declared = config.get("release_metadata", {}).get("evidence_documents", {})
    if not isinstance(declared, dict):
        raise ValueError("Additional release evidence must be a document mapping")
    names = {name.casefold() for name in reserved}
    documents = {}
    for name, item in declared.items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.json", name)
            or name.casefold() in names
        ):
            raise ValueError("Additional evidence must not replace existing release evidence")
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "sha256"}
            or not isinstance(item["path"], str)
            or not isinstance(item["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", item["sha256"])
        ):
            raise ValueError("Additional evidence needs an explicit path and SHA256")
        path = Path(item["path"])
        if path.is_symlink() or not path.is_file():
            raise ValueError("Additional evidence must be a regular document")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("Additional release evidence differs from its reviewed hash")
        value = json.loads(raw)
        if not isinstance(value, dict) or not value:
            raise ValueError("Additional release evidence must be a nonempty JSON object")
        documents[name] = value
        names.add(name.casefold())
    return documents


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
    from admission_profile import NATIVE_REVIEW_PROFILE

    required_review = validation.get("native_review_profile")
    if required_review not in (None, NATIVE_REVIEW_PROFILE):
        raise ValueError("Unknown release native-review profile")
    pipeline_path = config.get("autonomous_pipeline")
    manifest_path = config.get("autonomous_archive_manifest")
    snapshot_config = config.get("autonomous_snapshot")
    if pipeline_path is None and manifest_path is None and snapshot_config is None:
        if required_review is not None:
            raise ValueError("Reviewed-profile releases require archived pipeline evidence")
        return "assisted", {}
    if (
        not pipeline_path
        or (bool(manifest_path) == (snapshot_config is not None))
        or validation.get("accepted") is not True
    ):
        raise ValueError("Unattended provenance needs accepted, archived execution evidence")
    pipeline_path = Path(pipeline_path)
    snapshot = None
    if snapshot_config is not None:
        from snapshot_archive import verify_snapshot_archive

        if not isinstance(snapshot_config, dict) or set(snapshot_config) != {
            "restored",
            "transport",
            "recovery",
            "claim",
            "bootstrap",
        }:
            raise ValueError(
                "Snapshot provenance needs the original archive and recovery identities"
            )
        snapshot = verify_snapshot_archive(**snapshot_config)
        manifest_hash = snapshot.evidence["member_manifest_sha256"]
    else:
        manifest_path = Path(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("download_checked") is not True:
            raise ValueError("Unattended archive must have verified export readback")
        rows = {row["path"]: row for row in manifest["files"]}
        if len(rows) != len(manifest["files"]):
            raise ValueError("Ambiguous unattended archive paths")
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    def archived(path):
        path = Path(path)
        if snapshot is not None:
            relative = path.resolve().relative_to(snapshot.root.resolve()).as_posix()
            record = snapshot.read_json(relative)
            return record, snapshot.rows[relative]["sha256"]
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
    expected_stages = [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
        "native",
    ]
    if required_review is not None:
        expected_stages.append("native-review")
    if (
        pipeline.get("status") != "validated"
        or pipeline.get("autonomous") is not True
        or type(pipeline.get("operator_interventions")) is not int
        or pipeline["operator_interventions"] != 0
        or [stage.get("name") for stage in stages] != expected_stages
        or pipeline.get("native_review_profile") != required_review
        or any(stage.get("status") != "completed" for stage in stages)
        or native.get("status") != "native_validated_solver_attempt_recorded"
        or native.get("publication_ready") is not True
    ):
        raise ValueError("Execution does not establish a completed unattended pipeline")
    documents = {
        "autonomous-execution.json": {
            "pipeline_sha256": pipeline_hash,
            "native_result_sha256": native_hash,
            "archive_manifest_sha256": manifest_hash,
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
    if required_review is not None:
        from native_review import check_recorded

        proof = check_recorded(Path(config["native"]), required_review, validation["bundle_hash"])
        if validation.get("native_contract_review") != proof:
            raise ValueError("Native review differs from release validation evidence")
        if pipeline.get("native_review") != proof["result"]:
            raise ValueError("Pipeline admission differs from its native review")
        for relative, expected_hash in proof["evidence_files"].items():
            _, actual_hash = archived(pipeline_path.parent / relative)
            if actual_hash != expected_hash:
                raise ValueError("Native review differs from its original archive")
        documents["native-contract-review.json"] = proof
        documents["autonomous-execution.json"]["native_review_profile"] = required_review
    if snapshot is not None:
        documents["autonomous-execution.json"]["archive_format"] = "original-snapshot-v1"
        documents["autonomous-snapshot-provenance.json"] = snapshot.evidence
    return "unattended", documents


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
    repair_base = original
    supplement = None
    supplement_files = (
        "probe-supplement.json",
        "probe-coverage-baseline.json",
        "supplemented-probes.json",
    )
    if any((grading / name).exists() for name in supplement_files):
        from grading_protocol import check_repair_inventory
        from probe_coverage import ProbeSupplement, append_supplement, unexercised_scientific_checks

        if not all((grading / name).exists() for name in supplement_files):
            raise ValueError("Incomplete independent probe supplement evidence")
        baseline = read("probe-coverage-baseline.json")
        prior_candidate = Grader.model_validate(baseline["candidate"])
        check_repair_inventory(candidate.checks, prior_candidate.checks)
        if Probes.model_validate(baseline["original_probes"]) != original:
            raise ValueError("Supplement baseline differs from the original probe suite")
        targets = unexercised_scientific_checks(prior_candidate, baseline["controls"])
        if targets != baseline["targets"]:
            raise ValueError("Supplement targets differ from recorded executed coverage")
        supplement = ProbeSupplement.model_validate(read("probe-supplement.json"))
        repair_base = append_supplement(original, supplement, prior_candidate, targets)
        if Probes.model_validate(read("supplemented-probes.json")) != repair_base:
            raise ValueError("Supplemented suite differs from preserved original and additions")
    repair_path, revised_path = grading / "repair.json", grading / "repaired-probes.json"
    if repair_path.exists() != revised_path.exists():
        raise ValueError("Incomplete probe annotation repair evidence")
    repair = None
    if repair_path.exists():
        repair = GraderRepair.model_validate(read("repair.json"))
        expected_candidate, expected_suite = apply_probe_expectations(repair, repair_base)
        suite = Probes.model_validate(read("repaired-probes.json"))
        if candidate != expected_candidate or suite != expected_suite:
            raise ValueError("Repaired probes or grader differ from recorded repair")
    elif supplement is not None:
        raise ValueError("A probe supplement requires the existing quality-repair validation")
    check_probes(suite, candidate)
    expected = {p.name: p.model_dump() for p in suite.probes}
    seen = set()
    final_controls = read("final-controls.json")
    if supplement is not None and (
        unexercised_scientific_checks(candidate, final_controls)
        or not all(c.get("passed_control") is True for c in final_controls)
    ):
        raise ValueError("Supplement publication requires fresh complete passing negative coverage")
    for control in final_controls:
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
    if supplement is not None:
        documents["independent-probe-supplement.json"] = {
            **supplement.model_dump(),
            "coverage_targets": targets,
            "original_mutation_programs_preserved": True,
            "quality_repair_allowances": 1,
            "scope": "Additional independent challenges, not replacements or weaker acceptance criteria.",
        }
    if repair is not None:
        documents["initial-scientific-probes.json"] = original.model_dump()
        documents["probe-expectation-corrections.json"] = {
            "corrections": [item.model_dump() for item in repair.probe_expectations],
            "mutation_scripts_unchanged": True,
        }
        kinds = [
            {"name": old.name, "original": old.kind, "revised": new.kind}
            for old, new in zip(repair_base.probes, suite.probes, strict=True)
            if old.kind != new.kind
        ]
        if kinds:
            documents["probe-expectation-corrections.json"]["kind_corrections"] = kinds
        if repair.probe_concerns is not None:
            documents["probe-expectation-corrections.json"]["suite_concerns"] = {
                "original": original.concerns,
                "revised": suite.concerns,
            }
    return documents


def campaign_attribution(config, seed, materialization, *, experiment_root):
    """Carry explicit reviewed notices into native validation; never infer rights."""
    from pathlib import PurePosixPath

    selected = config.get("source_notices_file")
    if selected is None:
        return {"notebook": seed, "publication_status": "Not assessed; local validated task only"}
    if not isinstance(selected, str):
        raise ValueError("Source notices need a canonical experiment-relative path")
    relative = PurePosixPath(selected)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or str(relative) != selected
        or selected == "."
    ):
        raise ValueError("Source notices need a canonical experiment-relative path")
    selected_path = Path(experiment_root) / relative
    if selected_path.is_symlink() or not selected_path.resolve().is_relative_to(
        Path(experiment_root).resolve()
    ):
        raise ValueError("Source notices must be a regular file inside the experiment")
    notices = json.loads(selected_path.read_text())
    if not isinstance(notices, dict) or (
        notices.get("source_provenance") != seed.get("provenance")
        or not isinstance(seed.get("provenance"), dict)
        or notices.get("notebook_source_sha256") != seed.get("source_sha256")
    ):
        raise ValueError("Source notices differ from the selected notebook provenance/identity")
    notebook_license = notices.get("notebook_license", {})
    if not isinstance(notebook_license, dict) or not isinstance(notebook_license.get("text"), str):
        raise ValueError("Source notices require the original notebook license text")
    if not notebook_license["text"].strip() or hashlib.sha256(
        notebook_license["text"].encode()
    ).hexdigest() != notebook_license.get("sha256"):
        raise ValueError("Notebook license text differs from its recorded hash")
    reviewed = notices.get("reviewed_inputs")
    if not isinstance(reviewed, list) or not reviewed:
        raise ValueError("Source notices require explicitly reviewed input identities")
    permitted = set()
    for item in reviewed:
        if not isinstance(item, dict) or (
            not isinstance(item.get("sha256"), str)
            or len(item["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in item["sha256"])
            or type(item.get("bytes")) is not int
            or item["bytes"] < 0
            or any(
                not isinstance(item.get(k), str) or not item[k].strip()
                for k in ("source_url", "terms")
            )
        ):
            raise ValueError("Reviewed inputs require checksums, byte counts, sources and terms")
        permitted.add((item["sha256"], item["bytes"]))
    manifest = json.loads((Path(materialization) / "manifest.json").read_text())
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("Source attribution requires a materialized input inventory")
    actual = {(item["sha256"], item["bytes"]) for item in inputs}
    if not actual <= permitted:
        raise ValueError("Materialized inputs include data outside the reviewed identities")
    # Packaging independently rehashes these files before native execution.
    # Unused reviewed sources may retain their notices; copied inputs may be renamed.
    return notices
