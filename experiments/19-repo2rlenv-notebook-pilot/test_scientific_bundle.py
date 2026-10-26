"""Synthetic packaging boundaries: private assets and exact validation lineage."""

import hashlib
import json

import pytest
from scientific_bundle import package


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize("question_revision", [False, True])
@pytest.mark.parametrize("exclusions", [False, True])
@pytest.mark.parametrize("final_environment", [False, True])
def test_bundle_keeps_answers_private_and_requires_exact_controls(
    tmp_path, monkeypatch, question_revision, exclusions, final_environment
):
    materialized, grading, environment = [
        tmp_path / p for p in ("materialized", "grading", "environment")
    ]
    candidate = dict(
        disposition="ready",
        instruction="Scientific question",
        input_paths=["x.txt"],
        output_paths=["y.txt"],
        derive_code="pass",
        oracle_code="pass",
        rationale="Fixture",
    )
    item = dict(bytes=1, sha256=hashlib.sha256(b"1").hexdigest())
    manifest = dict(
        status="executed_requires_scientific_validation",
        inputs=[dict(item, path="x.txt")],
        reference=[dict(item, path="y.txt")],
        oracle_outputs=[dict(item, path="y.txt")],
    )
    entry = dict(
        distribution="fixture",
        path="fixture/tests/expected.txt",
        sha256="a" * 64,
        reason="PRIVATE observed expected output; unused fixture",
    )
    catalog_raw = b'{"files": [], "summary": {"priority_matches": []}}'
    if final_environment:
        from materialization_environment import binding, merge_exclusions, removal_receipt

        additional = [dict(entry, path="fixture/tests/final-expected.txt")]
        merged = merge_exclusions({"files": [entry] if exclusions else []}, additional)
        manifest["environment"] = {
            "exclusions": merged,
            "removal_receipt": removal_receipt(merged),
            "asset_summary": {"priority_matches": []},
            "asset_catalog": {
                "sha256": hashlib.sha256(catalog_raw).hexdigest(),
                "bytes": len(catalog_raw),
            },
            "asset_value_hints": {
                "findings": [{"source_text": "PRIVATE numeric answer fixture"}],
                "scope": "PRIVATE author inspection only",
            },
        }
        candidate["environment_review"] = {
            **binding(manifest),
            "assessment": "PRIVATE synthetic final-output assessment",
            "additional_exclusions": additional,
        }
    result = dict(status="materialized_requires_scientific_validation", cleanup_verified=True)
    records = []
    for name, value in [
        ("candidate.json", candidate),
        ("manifest.json", manifest),
        ("result.json", result),
    ]:
        path = materialized / name
        save(path, value)
        records.append(
            dict(
                path=name,
                bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    if final_environment:
        path = materialized / "dependency-assets-final.json"
        path.write_bytes(catalog_raw)
        records.append(
            dict(
                path=path.name,
                bytes=len(catalog_raw),
                sha256=hashlib.sha256(catalog_raw).hexdigest(),
            )
        )
    if final_environment:
        save(
            materialized / "asset-value-hints.json",
            {"findings": ["PRIVATE numeric answer fixture"]},
        )
    save(materialized / "artifact-manifest.json", dict(original_small_files=records))
    for kind, name in [("inputs", "x.txt"), ("reference", "y.txt")]:
        path = materialized / kind / name
        path.parent.mkdir()
        path.write_bytes(b"1")
    if question_revision:
        from question_repair import revise_question

        revised = tmp_path / "revised-materialization"
        revise_question(
            materialized,
            revised,
            {
                "disposition": "ready",
                "instruction": "Question with corrected convention",
                "rationale": "Source-grounded correction",
            },
        )
        assert json.loads((materialized / "candidate.json").read_text()) == candidate
        materialized = revised
        candidate = json.loads((materialized / "candidate.json").read_text())
    save(grading / "result.json", dict(status="grader_candidate_validated", cleanup_verified=True))
    grader = dict(
        instruction="Acceptance rules",
        grader_code="pass",
        checks=[dict(id="value", kind="scientific")],
    )
    save(grading / "final-candidate.json", grader)
    digest = hashlib.sha256((grading / "final-candidate.json").read_bytes()).hexdigest()
    controls = [
        dict(kind=kind, passed_control=True, candidate_sha256=digest)
        for kind in (
            "reference",
            "recomputed",
            "alternative",
            "empty",
            "misplaced",
            "missing",
            "probe",
        )
    ]
    save(grading / "final-controls.json", controls)
    (grading / "instruction.md").write_text(
        candidate["instruction"] + "\n\n## Acceptance rules\n\nAcceptance rules\n"
    )
    save(environment / "candidate/system-packages.json", [])
    (environment / "candidate/pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="0.0.1"\nrequires-python=">=3.13"\ndependencies=[]\n'
    )
    (environment / "trial").mkdir()
    (environment / "trial/uv.lock").write_text("fixture")
    if exclusions or final_environment:
        save(
            environment / "candidate/dependency-exclusions.json",
            {"files": [entry] if exclusions else []},
        )
        save(
            environment / "trial/dependency-exclusions-applied.json",
            {
                "files": [{key: entry[key] for key in ("distribution", "path", "sha256")}]
                if exclusions
                else [],
                "excluded_files_absent": True,
            },
        )
        (environment / "trial/dependency_assets.py").write_text("# Frozen helper fixture\n")
        save(
            environment / "artifact-manifest.json",
            {
                "files": [
                    {
                        "path": path.relative_to(environment).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    for path in environment.rglob("*")
                    if path.is_file()
                ]
            },
        )
    options = dict(
        materialization=materialized,
        grading=grading,
        environment=environment,
        destination=tmp_path / "bundles",
        name="fixture",
        revision="a" * 40,
        attribution={"notebook_license": {"text": "Fixture source notice\n"}},
    )
    task = package(**options)
    assert (task / "tests/reference/y.txt").read_bytes() == b"1"
    assert (task / "tests/inputs/x.txt").read_bytes() == b"1"
    assert json.loads((task / "tests/inputs-manifest.json").read_text()) == {
        "x.txt": hashlib.sha256(b"1").hexdigest()
    }
    assert not (task / "environment/inputs/y.txt").exists()
    assert not (task / "environment/reference").exists()
    assert "COPY inputs/" in (task / "environment/Dockerfile").read_text()
    instruction = (task / "instruction.md").read_text()
    assert instruction.startswith((grading / "instruction.md").read_text())
    assert "`/workspace/inputs/`" in instruction
    assert "`/workspace/outputs/`" in instruction
    assert "COPY inputs/ /workspace/inputs/" in (task / "environment/Dockerfile").read_text()
    if exclusions or final_environment:
        docker = (task / "environment/Dockerfile").read_text()
        assert "UV_NO_CACHE=1" in docker and "--no-cache-dir" in docker
        assert "/opt/venv/bin/python /opt/task-environment/dependency_assets.py" in docker
        assert "&& rm /opt/task-environment/dependency_assets.py" in docker
        public_manifest = (task / "environment/dependency-exclusions.json").read_text()
        assert "PRIVATE" not in public_manifest
        assert "reason" not in json.loads(public_manifest)["files"][0]
        assert len(json.loads(public_manifest)["files"]) == int(exclusions) + int(final_environment)
        if final_environment:
            assert any(
                row["path"] == "fixture/tests/final-expected.txt"
                for row in json.loads(public_manifest)["files"]
            )
            assert not (task / "environment/dependency-assets-final.json").exists()
            assert not any(p.name == "asset-value-hints.json" for p in task.rglob("*"))
            assert all(
                b"PRIVATE numeric answer fixture" not in p.read_bytes()
                for p in (task / "environment").rglob("*")
                if p.is_file()
            )
        assert (task / "environment/dependency_assets.py").read_bytes() == (
            environment / "trial/dependency_assets.py"
        ).read_bytes()
    assert "/workspace/outputs" in (task / "tests/verify.py").read_text()
    assert (task / "solution/oracle.py").exists()
    assert (task / "environment/LICENSE.source").read_text() == "Fixture source notice\n"
    assert (task / "environment/SOURCE-LICENSES.json").is_file()
    import tarfile
    from unittest.mock import Mock

    import run_scientific_native as native
    from repo2rlenv.emitter.bundle import inspect_bundle

    exporter = Mock()
    monkeypatch.setattr(native, "export_on_host", exporter)
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture/campaign")
    archive_root = tmp_path / "native"
    archive_root.mkdir()
    native.archive_task(task, archive_root, 9999999999)
    with tarfile.open(archive_root / "package/task.tar.gz") as archive:
        assert (
            archive.extractfile(task.name + "/instruction.md").read()
            == (task / "instruction.md").read_bytes()
        )
    assert json.loads((archive_root / "package/identity.json").read_text()) == inspect_bundle(task)
    exporter.assert_called_once_with(
        archive_root / "package", "s3://fixture/campaign/native/package", deadline=9999999999
    )
    controls[0]["candidate_sha256"] = "b" * 64
    save(grading / "final-controls.json", controls)
    with pytest.raises(ValueError, match="different grader"):
        package(**options)
    controls[0]["candidate_sha256"] = digest
    save(grading / "final-controls.json", controls)
    (grading / "instruction.md").write_text("Edited question")
    with pytest.raises(ValueError, match="validated composition"):
        package(**options)
