"""A new-profile release requires an accepting original bound worker review."""

import json
import time

import native_review as module
import pytest
from admission_profile import NATIVE_REVIEW_PROFILE, task_review_profile
from release_metadata import release_execution_provenance
from review_packet import ReviewPacket
from test_native_review import make_native, save, verdict


@pytest.fixture
def native(tmp_path):
    return make_native(tmp_path)


def record_review(native):
    root = native.parent / "native-review"
    evidence, _ = module.collect(native)
    packet = ReviewPacket(root / "review-packets", evidence, time.time() + 60)
    review = verdict(evidence)
    result = dict(
        status="validated",
        profile=NATIVE_REVIEW_PROFILE,
        bundle_hash=evidence["bundle_hash"],
        rollout=review.rollout,
    )
    save(root / "input.json", evidence)
    save(root / "result.json", result)
    save(root / "review.json", review.model_dump())
    save(root / "review/input.json", packet.model_context)
    save(root / "review/artifact-stage/artifact.json", {"artifact": review.model_dump()})
    return root, evidence["bundle_hash"], result


def test_new_task_profile_requires_archived_pipeline_even_for_assisted_release(native):
    assert task_review_profile(native / "tasks/fixture") == NATIVE_REVIEW_PROFILE
    with pytest.raises(ValueError, match="archived pipeline"):
        release_execution_provenance({}, {"native_review_profile": NATIVE_REVIEW_PROFILE})
    with pytest.raises(ValueError):
        module.check_recorded(native, NATIVE_REVIEW_PROFILE, "sha256:" + "a" * 64)


def test_recorded_review_is_revalidated_without_model_or_reward_changes(native):
    root, bundle_hash, result = record_review(native)
    before = {p: p.read_bytes() for p in native.rglob("*") if p.is_file()}
    proof = module.check_recorded(native, NATIVE_REVIEW_PROFILE, bundle_hash)
    assert proof["result"] == result
    assert proof["original_rewards"] == [1.0, 0.0, 0.0]
    assert "native-review/review/artifact-stage/artifact.json" in proof["evidence_files"]
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert (root / "review.json").is_file()


@pytest.mark.parametrize(
    "defect",
    [
        "profile",
        "bundle",
        "rejected",
        "unknown",
        "worker",
        "input",
        "packet",
        "outcome",
        "source",
        "missing",
    ],
)
def test_recorded_review_refuses_stale_incomplete_or_nonaccepting_evidence(native, defect):
    root, bundle_hash, result = record_review(native)
    if defect == "profile":
        result["profile"] = "unknown"
    elif defect == "bundle":
        result["bundle_hash"] = "sha256:" + "a" * 64
    elif defect == "rejected":
        result["status"] = "rejected"
    elif defect == "unknown":
        r = json.loads((root / "review.json").read_text())
        r["verifier"]["status"] = "unknown"
        save(root / "review.json", r)
        save(root / "review/artifact-stage/artifact.json", {"artifact": r})
    elif defect == "worker":
        save(root / "review/artifact-stage/artifact.json", {"artifact": {"different": True}})
    elif defect == "input":
        save(root / "input.json", {"another": "task"})
    elif defect == "packet":
        path = next((root / "review-packets").glob("*/0000.json"))
        path.chmod(0o600)
        path.write_text('"changed packet"')
    elif defect == "outcome":
        result["rollout"] = "legitimate_success"
    elif defect == "source":
        (native / "tasks/fixture/instruction.md").write_text("Changed task")
    else:
        (root / "review/artifact-stage/artifact.json").unlink()
    save(root / "result.json", result)
    with pytest.raises((ValueError, KeyError)):
        module.check_recorded(native, NATIVE_REVIEW_PROFILE, bundle_hash)


def release_fixture(native):
    root = native.parent
    summary = json.loads((native / "result.json").read_text())
    summary["publication_ready"] = True
    save(native / "result.json", summary)
    _, bundle_hash, result = record_review(native)
    proof = module.check_recorded(native, NATIVE_REVIEW_PROFILE, bundle_hash)
    source = {"source_sha256": "a" * 64}
    pipeline = dict(
        status="validated",
        source=source,
        autonomous=True,
        operator_interventions=0,
        factory_revision="b" * 40,
        native_review_profile=NATIVE_REVIEW_PROFILE,
        native_review=result,
        stages=[
            dict(name=name, status="completed")
            for name in [
                "preparation",
                "setup",
                "replay",
                "specification",
                "construction",
                "grading",
                "native",
                "native-review",
            ]
        ],
    )
    save(root / "pipeline.json", pipeline)
    save(root / "seed.json", [source])
    rows = []
    for path in [
        root / "pipeline.json",
        native / "result.json",
        *sorted((root / "native-review").rglob("*.json")),
    ]:
        rows.append(
            dict(
                path=path.relative_to(root).as_posix(),
                bytes=path.stat().st_size,
                sha256=module.digest(path),
            )
        )
    save(root / "archive.json", dict(download_checked=True, files=rows))
    return dict(
        autonomous_pipeline=str(root / "pipeline.json"),
        autonomous_archive_manifest=str(root / "archive.json"),
        native=str(native),
        release_metadata={"seed_file": str(root / "seed.json")},
    ), dict(
        accepted=True,
        bundle_hash=bundle_hash,
        native_review_profile=NATIVE_REVIEW_PROFILE,
        native_contract_review=proof,
    )


def test_new_profile_release_carries_the_archived_review(native):
    config, validation = release_fixture(native)
    provenance, documents = release_execution_provenance(config, validation)
    assert provenance == "unattended"
    assert documents["autonomous-execution.json"]["native_review_profile"] == NATIVE_REVIEW_PROFILE
    assert documents["native-contract-review.json"] == validation["native_contract_review"]


@pytest.mark.parametrize(
    "defect",
    [
        "missing_stage",
        "missing_profile",
        "wrong_pipeline_result",
        "unarchived_review",
        "wrong_validation",
    ],
)
def test_release_cannot_bypass_or_downgrade_the_new_review(native, defect):
    config, validation = release_fixture(native)
    root = native.parent
    path = root / "pipeline.json"
    pipeline = json.loads(path.read_text())
    if defect == "missing_stage":
        pipeline["stages"].pop()
    elif defect == "missing_profile":
        pipeline.pop("native_review_profile")
    elif defect == "wrong_pipeline_result":
        pipeline["native_review"] = {"status": "validated"}
    elif defect == "wrong_validation":
        validation["native_contract_review"] = {}
    else:
        p = root / "archive.json"
        archive = json.loads(p.read_text())
        archive["files"] = [
            row for row in archive["files"] if row["path"] != "native-review/review.json"
        ]
        save(p, archive)
    save(path, pipeline)
    p = root / "archive.json"
    archive = json.loads(p.read_text())
    row = next(row for row in archive["files"] if row["path"] == "pipeline.json")
    row.update(bytes=path.stat().st_size, sha256=module.digest(path))
    save(p, archive)
    with pytest.raises(ValueError):
        release_execution_provenance(config, validation)
