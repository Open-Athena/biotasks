"""Read-only acceptance gate for the new scientific release; never uploads."""

import hashlib
import json
import sys
from pathlib import Path

from admission_profile import task_review_profile
from grader_support import MANIFEST, MODULE, load_support
from release_review import check_final_review
from repo2rlenv.emitter.bundle import inspect_bundle
from scientific_bundle import runtime_instruction

native, task, grading = map(Path, sys.argv[1:])


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


identity = inspect_bundle(task)
assert identity["integrity_passed"]
summary = read(native / "result.json")
assert summary["status"] == "native_validated_solver_attempt_recorded"
assert summary["publication_ready"] is True
assert [c["agent"] for c in summary["controls"]] == ["oracle", "nop"]
assert [c["reward"] for c in summary["controls"]] == [1, 0]
assert all(c["passed"] for c in summary["controls"])
assert summary["solver"]["agent"] == "terminus-2"
records = []
for item in [*summary["controls"], summary["solver"]]:
    agent = item["agent"]
    raw_path = native / item["result_path"]
    raw = read(raw_path)
    receipt = read(native / agent / "trial.json")
    assert receipt["state"] == "completed"
    assert receipt["bundle_hash"] == identity["bundle_hash"]
    assert receipt["result_sha256"] == digest(raw_path)
    assert receipt["agent"] == raw["config"]["agent"]["name"] == agent
    reward = (raw.get("verifier_result") or {}).get("rewards", {}).get("reward")
    exception = (raw.get("exception_info") or {}).get("exception_type")
    assert reward == item["reward"] == receipt["reward"]
    assert exception == item["exception_type"] == receipt["exception_type"]
    assert exception in ({None, "AgentTimeoutError"} if agent == "terminus-2" else {None})
    assert read(native / agent / "remote-job.json")["cleanup"]["passed"] is True
    assert item["cleanup_verified"] is True
    records.append(
        dict(
            agent=agent,
            reward=reward,
            exception_type=exception,
            bundle_hash=identity["bundle_hash"],
            result_sha256=digest(raw_path),
        )
    )
claims = [read(p) for p in (native / "trial-claims").glob("*.json")]
assert len(claims) == 3 and all(c["cleanup_verified"] for c in claims)
assert sum(c["solving"] for c in claims) == 1
result = read(grading / "result.json")
assert result["status"] == "grader_candidate_validated" and result["cleanup_verified"]
controls = read(grading / "final-controls.json")
candidate = read(grading / "final-candidate.json")
check_final_review(grading)
assert controls and all(c["passed_control"] for c in controls)
assert all(c["candidate_sha256"] == digest(grading / "final-candidate.json") for c in controls)
assert {"reference", "recomputed", "alternative", "empty", "misplaced", "missing", "probe"} <= {
    c["kind"] for c in controls
}
assert (task / "tests/grade.py").read_text() == candidate["grader_code"] + "\n"
assert (task / "instruction.md").read_text() == runtime_instruction(
    (grading / "instruction.md").read_text()
)
assert read(task / "tests/checks.json") == candidate["checks"]
support = load_support(grading, result.get("parsing_support"))
assert load_support(task / "tests", support) == support
if support is not None:
    assert (task / "tests" / MODULE).read_bytes() == (grading / MODULE).read_bytes()
    assert read(task / "tests" / MANIFEST) == support
    assert all(c["execution"].get("parsing_support") == support for c in controls)
profile = task_review_profile(task)
native_review = None
if profile is not None:
    from native_review import check_recorded

    native_review = check_recorded(native, profile, identity["bundle_hash"])
print(
    json.dumps(
        dict(
            bundle_hash=identity["bundle_hash"],
            native_trials=records,
            scientific_controls=len(controls),
            source_coverage_review_verified=True,
            scientific_admission_review_verified=True,
            asset_value_hints_review_verified=True,
            executed_scientific_negative_coverage_verified=True,
            native_review_profile=profile,
            native_contract_review=native_review,
            accepted=True,
        ),
        indent=2,
    )
)
