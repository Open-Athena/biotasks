"""Admit an explicitly tested source delta without relabeling old live proofs.

This is operator-side launch verification, excluded from the scientific payload.
It permits only the recorded candidate; unknown source changes remain blockers.
"""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def git_source(repo, revision, path):
    return subprocess.check_output(["git", "show", revision + ":" + path], cwd=repo)


def selected_ast(raw, selector):
    nodes = ast.parse(raw).body
    for name in selector.split("."):
        selected = next(n for n in nodes if getattr(n, "name", None) == name)
        nodes = getattr(selected, "body", [])
    return ast.dump(selected, include_attributes=False)


def candidate_admission(repo, runtime):
    repo = Path(repo)
    experiment = repo / PREFIX
    old = load(experiment / "panel-rounds/100/runtime-identity.json")["runtime_files"]
    construction = load(experiment / "factory-checks/construction-repair/input-handoff-checks.json")
    reader = load(experiment / "factory-checks/release-packet/offline-checks.json")
    controls = load(
        experiment / "factory-checks/setup-control-budget/live-check-configuration.json"
    )
    control_result = load(
        experiment / "factory-checks/setup-control-budget/integration-summary.json"
    )
    cleanup_raw = (
        experiment / "factory-checks/setup-control-budget/live-fresh-provider-cleanup.json"
    ).read_bytes()
    cleanup = json.loads(cleanup_raw)
    prompt = load(experiment / "factory-checks/reference-preservation/candidate.json")
    assert (
        construction["affected_tests_passed"] == 373
        and construction["default_project_tests_passed"] == 234
    )
    assert reader["affected_tests_passed"] == 205 and reader["default_project_tests_passed"] == 234
    assert control_result["new_model_calls"] == 0
    assert len(control_result["cases"]) == 3 and all(
        row["passed"] for row in control_result["cases"]
    )
    assert control_result["source_configuration_sha256"] == digest(
        (
            experiment / "factory-checks/setup-control-budget/live-check-configuration.json"
        ).read_bytes()
    )
    assert control_result["fresh_cleanup_sha256"] == digest(cleanup_raw)
    assert (
        cleanup["complete"]
        and cleanup["fresh_original_id_absent"]
        and cleanup["fresh_owner_list_empty"]
    )
    expected = dict(construction["source_sha256"])
    expected.update({PREFIX + key: value for key, value in reader["source_sha256"].items()})
    expected[PREFIX + "reference_setup.py"] = controls["source_sha256"]["reference_setup.py"]
    expected[PREFIX + "test_reference_setup.py"] = digest(
        git_source(repo, controls["source_runtime_revision"], PREFIX + "test_reference_setup.py")
    )
    expected[prompt["prompt"]] = prompt["candidate_sha256"]
    added = set(runtime) - set(old)
    changed = {name for name in runtime.keys() & old.keys() if runtime[name] != old[name]}
    assert not (set(old) - set(runtime)), "Unexpected runtime removal"
    assert added | changed == set(expected), "Unknown or missing candidate runtime delta"
    assert all(runtime[name] == value for name, value in expected.items()), (
        "Untested candidate bytes"
    )
    assert all(digest((repo / name).read_bytes()) == value for name, value in runtime.items())
    baseline = controls["source_runtime_revision"]
    boundaries = {}
    for filename, selector in [
        ("run_reference_setup.py", "Remote"),
        ("run_reference_setup.py", "run"),
        ("run_autonomous.py", "Pipeline.config_for"),
        ("run_autonomous.py", "Pipeline.step"),
    ]:
        before = git_source(repo, baseline, PREFIX + filename)
        after = (experiment / filename).read_bytes()
        assert selected_ast(before, selector) == selected_ast(after, selector)
        boundaries[filename + ":" + selector] = "unchanged_AST"
    previous_packet = git_source(
        repo, "2e31d593a4a452553d7c5a84bc4d58423a0014b4", PREFIX + "review_packet.py"
    )
    current_packet = (experiment / "review_packet.py").read_bytes()
    for method in (
        "__init__",
        "remaining",
        "document",
        "reconstruct",
        "read_review_evidence",
        "tools",
        "handlers",
    ):
        selector = "ReviewPacket." + method
        assert selected_ast(previous_packet, selector) == selected_ast(current_packet, selector)
        boundaries["review_packet.py:" + selector] = "unchanged_AST"
    for filename in (
        "preflight.py",
        "reference_remote.py",
        "daytona_session.py",
        "upload_transfer.py",
        "run_scientific_native.py",
        "iris_execution.py",
    ):
        assert git_source(repo, baseline, PREFIX + filename) == (experiment / filename).read_bytes()
        boundaries[filename] = "unchanged_complete_file"
    return {
        "old": old,
        "candidate": runtime,
        "allowed_source_deltas": expected,
        "boundaries": boundaries,
        "existing_provider_controls": {
            "configuration_sha256": digest(
                (
                    experiment / "factory-checks/setup-control-budget/live-check-configuration.json"
                ).read_bytes()
            ),
            "result_sha256": digest(
                (
                    experiment / "factory-checks/setup-control-budget/integration-summary.json"
                ).read_bytes()
            ),
            "cleanup_sha256": digest(cleanup_raw),
        },
        "new_construction_repair_live_qualified": False,
        "old_proof_reclassified": False,
    }


def check_source(admission, name, expected):
    actual = admission["candidate"][name]
    if actual == expected:
        return "exact_previous_proof_bytes"
    assert admission["old"].get(name) == expected, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual, "Unadmitted source change"
    return "explicit_tested_candidate_delta_not_new_live_proof"
