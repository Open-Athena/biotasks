"""Admit only the recorded idle-lifecycle change over a qualified predecessor."""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
BASE = "23fd6d275b8d7bafca6186595bbd0e18668c8bcf"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def prove_idle_only(before, after):
    old, new = ast.parse(before), ast.parse(after)
    entries = [
        n for n in ast.walk(old) if isinstance(n, ast.keyword) and n.arg == "auto_stop_interval"
    ]
    assert len(entries) == 1
    assert isinstance(entries[0].value, ast.Constant) and entries[0].value.value == 30
    entries[0].value = ast.Constant(0)
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False), (
        "Only disabling authoring idle-stop is admitted; TTL, resources and all other behavior must match"
    )


def candidate_admission(repo, runtime):
    repo = Path(repo)
    experiment = repo / PREFIX
    baseline = load(experiment / "panel-rounds/101/runtime-identity.json")["runtime_files"]
    expected = load(
        experiment / "factory-checks/author-idle-lifecycle/candidate-runtime-identity.json"
    )
    checks = load(experiment / "factory-checks/author-idle-lifecycle/offline-checks.json")
    assert runtime == expected["runtime_files"] and set(runtime) == set(baseline)
    changed = {p for p in runtime if runtime[p] != baseline[p]}
    assert changed == {PREFIX + "run_reference_setup.py", PREFIX + "test_reference_setup.py"}
    assert all(digest((repo / p).read_bytes()) == h for p, h in runtime.items())
    assert checks["affected_tests_passed"] == 127 and checks["all_scientific_prompts_identical"]
    assert checks["complete_runtime_ast_equal_after_normalizing_only_idle_stop"]
    assert all(
        checks["runtime_delta"][p] == {"old": baseline[p], "new": runtime[p]} for p in changed
    )
    before = subprocess.check_output(
        ["git", "show", BASE + ":" + PREFIX + "run_reference_setup.py"], cwd=repo
    )
    assert digest(before) == baseline[PREFIX + "run_reference_setup.py"]
    prove_idle_only(before, (experiment / "run_reference_setup.py").read_bytes())
    prior = load(experiment / "panel-rounds/101/source-admission.json")
    assert (
        digest((experiment / "panel-rounds/101/runtime_admission.py").read_bytes())
        == prior["admission_helper_sha256"]
    )
    qualified = load(experiment / "panel-rounds/101/result-198.json")
    assert qualified["factory_runtime_revision"] == BASE and qualified["fully_qualified_task"]
    assert load(experiment / "autonomous-runs/198/scientific-release-check.json")["accepted"]
    assert load(experiment / "autonomous-runs/198/hub-download-verification.json")["verified"]
    allowed = dict(prior["candidate_deltas"])
    allowed.update({p: runtime[p] for p in changed})
    return {
        "old": load(experiment / "panel-rounds/100/runtime-identity.json")["runtime_files"],
        "predecessor": baseline,
        "candidate": runtime,
        "allowed_source_deltas": allowed,
        "baseline_source_admission_sha256": digest(
            (experiment / "panel-rounds/101/source-admission.json").read_bytes()
        ),
        "complete_runtime_ast_equal_after_normalizing_only_idle_stop": True,
        "all_scientific_prompts_identical": True,
        "new_construction_repair_live_qualified": False,
        "new_idle_lifecycle_live_qualified": False,
    }


def check_source(admission, name, expected):
    actual = admission["candidate"][name]
    if actual == expected:
        return "exact_previous_proof_bytes"
    assert expected in {admission["old"].get(name), admission["predecessor"].get(name)}, (
        "Proof belongs to an unknown source family"
    )
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_new_live_proof"
