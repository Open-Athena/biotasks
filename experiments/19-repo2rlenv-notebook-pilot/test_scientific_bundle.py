"""Synthetic packaging boundaries: private assets and exact validation lineage."""

import hashlib
import json

import pytest
from scientific_bundle import package


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize("question_revision", [False, True])
def test_bundle_keeps_answers_private_and_requires_exact_controls(
    tmp_path, monkeypatch, question_revision
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
    assert not (task / "environment/reference").exists()
    assert "COPY inputs/" in (task / "environment/Dockerfile").read_text()
    instruction = (task / "instruction.md").read_text()
    assert instruction.startswith((grading / "instruction.md").read_text())
    assert "`/workspace/inputs/`" in instruction
    assert "`/workspace/outputs/`" in instruction
    assert "COPY inputs/ /workspace/inputs/" in (task / "environment/Dockerfile").read_text()
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
