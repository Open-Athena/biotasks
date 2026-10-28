"""Admission, source binding and read-only worker tests; no scientific execution."""

import asyncio
import json
import time

import native_review as review_module
import pytest
from admission_profile import NATIVE_REVIEW_PROFILE
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, inspect_bundle, write_bundle
from repo2rlenv.quality.loop.artifacts import parse_task
from repo2rlenv.quality.loop.models import Review


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def make_native(tmp_path):
    root = tmp_path / "native"
    bundle = TaskBundle(
        name="fixture",
        org="fixture",
        instruction="Compute the required quantity using supplied observations.",
        files={
            "solution/solve.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
            "tests/test.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
            "environment/Dockerfile": TaskFile.text("FROM scratch\n"),
            "environment/observations.bin": TaskFile(b"\xff\0\x01"),
        },
        metadata={
            "recipe": "fixture",
            "recipe_version": "1",
            "reward_kinds": ["binary"],
            "native_review_profile": NATIVE_REVIEW_PROFILE,
        },
    )
    task = write_bundle(bundle, root / "tasks")
    checksum = parse_task(task).checksum
    save(root / "package/identity.json", inspect_bundle(task))
    rows = []
    for agent, reward in (("oracle", 1.0), ("nop", 0.0), ("terminus-2", 0.0)):
        path = root / agent / "trial/result.json"
        save(
            path,
            {
                "task_checksum": checksum,
                "config": {"agent": {"name": agent, "model_name": "fixture"}},
                "verifier_result": {"rewards": {"reward": reward}},
                "exception_info": None,
            },
        )
        save(path.parent / "verifier/report.json", {"passed": reward == 1.0})
        save(
            path.parent / "agent/trajectory.json",
            {"steps": [{"command": "compute an incorrect quantity", "output": "completed"}]},
        )
        (path.parent / "agent/exit-code.txt").write_text("0")
        rows.append(
            dict(
                agent=agent,
                reward=reward,
                exception_type=None,
                cleanup_verified=True,
                result_path=path.relative_to(root).as_posix(),
            )
        )
    save(
        root / "result.json",
        dict(status="native_validated_solver_attempt_recorded", controls=rows[:2], solver=rows[2]),
    )
    return root


@pytest.fixture
def native(tmp_path):
    return make_native(tmp_path)


def assessment(path, quote, *, status="pass"):
    return dict(
        status=status,
        score=3,
        explanation="Synthetic evidence",
        evidence=[dict(path=path, quote=quote)],
    )


def verdict(evidence, *, rollout="legitimate_failure", unknown=False, blocking=False):
    documents = evidence["documents"]
    contract = "task/instruction.md"
    verifier = "evidence/2-rollout/verifier/report.json"
    trajectory = "evidence/2-rollout/agent/trajectory.json"
    result = dict(
        summary="Synthetic review, not a model or scientific validation",
        task=assessment(contract, documents[contract]),
        verifier=assessment(verifier, documents[verifier], status="unknown" if unknown else "pass"),
        leakage=assessment(trajectory, documents[trajectory]),
        rollout=rollout,
        issues=[],
        probes=[],
        read_requests=[],
    )
    if blocking:
        result["issues"].append(
            dict(
                category="verifier",
                severity="blocking",
                problem="Synthetic public-rule mismatch",
                repair="Review the corresponding rule in the owning worker",
                evidence=[dict(path=contract, quote=documents[contract])],
            )
        )
    return Review.model_validate(result)


def test_real_upstream_binding_and_complete_documents(native):
    evidence, trials = review_module.collect(native)
    assert [trial.role for trial in trials] == ["oracle", "baseline", "rollout"]
    assert all(trial.bundle_hash == evidence["bundle_hash"] for trial in trials)
    assert trials[-1].binding == "harbor_checksum"
    binary = next(row for row in evidence["inventory"] if row["key"].endswith("observations.bin"))
    assert not binary["text_available"] and binary["bytes"] == 3
    assert binary["key"] not in evidence["documents"]
    review_module.validate(verdict(evidence), evidence, trials)
    assert review_module.admission(verdict(evidence)) == "validated"


def test_successful_solver_still_requires_a_sound_review(native):
    summary = json.loads((native / "result.json").read_text())
    path = native / summary["solver"]["result_path"]
    trial = json.loads(path.read_text())
    trial["verifier_result"]["rewards"]["reward"] = 1.0
    save(path, trial)
    summary["solver"]["reward"] = 1.0
    save(native / "result.json", summary)
    evidence, trials = review_module.collect(native)
    accepted = verdict(evidence, rollout="legitimate_success")
    review_module.validate(accepted, evidence, trials)
    assert review_module.admission(accepted) == "validated"
    held = verdict(evidence, rollout="legitimate_success", unknown=True)
    review_module.validate(held, evidence, trials)
    assert review_module.admission(held) == "needs_evidence"


@pytest.mark.parametrize("change", ["cross_task", "reward", "agent", "cleanup", "path", "control"])
def test_collect_refuses_unbound_or_invalid_trials(native, change):
    summary_path = native / "result.json"
    summary = json.loads(summary_path.read_text())
    trial_path = native / summary["solver"]["result_path"]
    trial = json.loads(trial_path.read_text())
    if change == "cross_task":
        trial["task_checksum"] = "different-source"
    elif change == "reward":
        summary["solver"]["reward"] = 1.0
    elif change == "agent":
        summary["solver"]["agent"] = "different-agent"
    elif change == "cleanup":
        summary["solver"]["cleanup_verified"] = False
    elif change == "path":
        summary["solver"]["result_path"] = "../outside.json"
    else:
        p = native / summary["controls"][0]["result_path"]
        d = json.loads(p.read_text())
        d["verifier_result"]["rewards"]["reward"] = 0.0
        save(p, d)
        summary["controls"][0]["reward"] = 0.0
    save(summary_path, summary)
    save(trial_path, trial)
    with pytest.raises(ValueError):
        review_module.collect(native)


@pytest.mark.parametrize("change", ["bytes", "mode", "new_file", "link", "missing"])
def test_review_refuses_changed_evidence(native, change):
    evidence, _ = review_module.collect(native)
    path = native / "tasks/fixture/instruction.md"
    if change == "bytes":
        path.write_text("Another scientific contract")
    elif change == "mode":
        path.chmod(0o755)
    elif change == "new_file":
        (path.parent / "environment/unreviewed.txt").write_text("new answer fixture")
    elif change == "link":
        path.unlink()
        path.symlink_to(native / "result.json")
    else:
        path.unlink()
    with pytest.raises(ValueError):
        review_module.recheck(native, evidence["inventory"])


@pytest.mark.parametrize(
    "rollout,unknown,blocking,expected",
    [
        ("legitimate_failure", False, False, "validated"),
        ("legitimate_failure", True, False, "needs_evidence"),
        ("legitimate_failure", False, True, "rejected"),
        ("task_defect", False, True, "rejected"),
        ("reward_hack", False, True, "rejected"),
        ("insufficient_evidence", False, False, "needs_evidence"),
        ("incomplete", False, False, "needs_evidence"),
        ("not_run", False, False, "needs_evidence"),
        ("infrastructure_failure", False, False, "infrastructure_failed"),
    ],
)
def test_gate_never_substitutes_reward_for_suitability(
    native, rollout, unknown, blocking, expected
):
    evidence, trials = review_module.collect(native)
    review = verdict(evidence, rollout=rollout, unknown=unknown, blocking=blocking)
    review_module.validate(review, evidence, trials)
    assert review_module.admission(review) == expected


@pytest.mark.parametrize(
    "change", ["wrong_quote", "missing_trace", "wrong_outcome", "request_reads", "bare_defect"]
)
def test_invalid_or_unsupported_approval_is_refused(native, change):
    evidence, trials = review_module.collect(native)
    review = verdict(evidence)
    if change == "wrong_quote":
        review.task.evidence[0].quote = "invented rule"
    elif change == "missing_trace":
        review.leakage.evidence = review.task.evidence
    elif change == "wrong_outcome":
        review.rollout = "legitimate_success"
    elif change == "bare_defect":
        review.rollout = "task_defect"
    else:
        review.read_requests = [dict(path="missing", query=None, start_line=1, end_line=2)]
    with pytest.raises(ValueError):
        review_module.validate(review, evidence, trials)


@pytest.mark.parametrize("outcome", ["legitimate_failure", "task_defect"])
def test_session_uses_read_only_tools_and_preserves_original_reward(
    native, tmp_path, monkeypatch, outcome
):
    source_before = {p: p.read_bytes() for p in native.rglob("*") if p.is_file()}
    evidence, _ = review_module.collect(native)

    async def fake_stage(**kwargs):
        assert "shell" not in kwargs
        assert kwargs["max_requests"] is None
        assert kwargs["schema"] is Review
        assert kwargs["limits"].max_output_tokens is None
        assert kwargs["limits"].reasoning_effort == "high"
        assert set(kwargs["extra_handlers"]) == {
            "read_review_evidence",
            "read_review_evidence_batch",
        }
        # The actual packet handler, not a fake summarized trace, serves reads.
        raw = await kwargs["extra_handlers"]["read_review_evidence"](
            field="documents", pointer="/task~1instruction.md", end_column=None
        )
        assert "Compute the required quantity" in raw
        review = verdict(evidence, rollout=outcome, blocking=outcome == "task_defect")
        await kwargs["validate"](review)
        return review

    monkeypatch.setattr(review_module, "stage", fake_stage)
    result = asyncio.run(
        review_module.run(
            {"reasoning_effort": "high", "request_timeout_seconds": 600},
            native=native,
            root=tmp_path / "review",
            endpoint="must-not-connect",
            credential="unused",
            deadline=time.time() + 60,
            complete=object(),
        )
    )
    assert result["status"] == ("validated" if outcome == "legitimate_failure" else "rejected")
    assert all(p.read_bytes() == raw for p, raw in source_before.items())
    assert json.loads((tmp_path / "review/review.json").read_text())["rollout"] == outcome
