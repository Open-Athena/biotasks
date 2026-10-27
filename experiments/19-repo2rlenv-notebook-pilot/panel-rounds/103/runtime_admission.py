"""Admit only tested same-empty-session creation reconciliation over round102.

This is operator admission, outside the scientific payload. Original provider
proofs remain historical; the new three-case control is an additional proof.
"""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
BASE = "d22dce7e2003c00a7d217b186546f7de9b67b33d"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def prove_creation_only(before, after):
    old, new = ast.parse(before), ast.parse(after)
    old_test = ast.parse(
        "not transient_connection_error(error) or "
        "not inspect.iscoroutinefunction(getattr(process, 'get_session', None))",
        mode="eval",
    ).body
    assignment = ast.parse(
        "recoverable = transient_connection_error(error) or "
        "(creation == 1 and isinstance(error, DaytonaConflictError))"
    ).body[0]
    new_test = ast.parse(
        "not recoverable or not inspect.iscoroutinefunction(getattr(process, 'get_session', None))",
        mode="eval",
    ).body

    class Normalize(ast.NodeTransformer):
        imports = 0
        recoveries = 0

        def visit_ImportFrom(self, node):
            if node.module == "daytona.common.errors":
                assert [n.name for n in node.names] == ["DaytonaNotFoundError"]
                node.names.insert(0, ast.alias(name="DaytonaConflictError"))
                self.imports += 1
            return node

        def visit_If(self, node):
            self.generic_visit(node)
            if ast.dump(node.test) == ast.dump(old_test):
                assert len(node.body) == 1 and isinstance(node.body[0], ast.Raise)
                node.test = new_test
                self.recoveries += 1
                return [assignment, node]
            return node

    transform = Normalize()
    normalized = transform.visit(old)
    assert transform.imports == transform.recoveries == 1
    assert ast.dump(normalized, include_attributes=False) == ast.dump(
        new, include_attributes=False
    ), "Unknown transport change beyond retry-create conflict reconciliation"


def candidate_admission(repo, runtime):
    repo = Path(repo)
    experiment = repo / PREFIX
    baseline = load(experiment / "panel-rounds/102/runtime-identity.json")["runtime_files"]
    expected = load(
        experiment / "factory-checks/session-create-conflict/candidate-runtime-identity.json"
    )
    checks = load(experiment / "factory-checks/session-create-conflict/offline-checks.json")
    assert runtime == expected["runtime_files"] and set(runtime) == set(baseline)
    changed = {p for p in runtime if runtime[p] != baseline[p]}
    assert changed == {PREFIX + "daytona_session.py", PREFIX + "test_daytona_session.py"}
    assert all(digest((repo / p).read_bytes()) == h for p, h in runtime.items())
    assert checks["affected_tests_passed"] == 182 and checks["all_scientific_prompts_unchanged"]
    before = subprocess.check_output(
        ["git", "show", BASE + ":" + PREFIX + "daytona_session.py"], cwd=repo
    )
    assert digest(before) == baseline[PREFIX + "daytona_session.py"]
    prove_creation_only(before, (experiment / "daytona_session.py").read_bytes())
    root = experiment / "factory-checks/session-create-conflict"
    configuration = load(root / "live-check-configuration.json")
    proof = load(root / "integration-summary.json")
    cleanup = (root / "live-fresh-provider-cleanup.json").read_bytes()
    clean = json.loads(cleanup)
    assert proof["status"] == "provider_boundary_observed_not_scientific_qualification"
    assert proof["source_configuration_sha256"] == digest(
        (root / "live-check-configuration.json").read_bytes()
    )
    assert proof["fresh_cleanup_sha256"] == digest(cleanup)
    assert (
        clean["complete"] and clean["fresh_original_id_absent"] and clean["fresh_owner_list_empty"]
    )
    assert len(proof["cases"]) == 3 and all(row["passed"] for row in proof["cases"])
    assert any(row["actual_provider_conflict"] for row in proof["cases"])
    assert all(
        row["observed_executions"] == row["command_submission_attempts"] == 1
        for row in proof["cases"]
    )
    assert (
        configuration["source_sha256"][PREFIX + "daytona_session.py"]
        == runtime[PREFIX + "daytona_session.py"]
    )
    prior = load(experiment / "panel-rounds/102/source-admission.json")
    assert (
        digest((experiment / "panel-rounds/102/runtime_admission.py").read_bytes())
        == prior["admission_helper_sha256"]
    )
    original = load(experiment / "panel-rounds/101/source-admission.json")
    allowed = dict(original["candidate_deltas"])
    first = load(experiment / "panel-rounds/101/runtime-identity.json")["runtime_files"]
    allowed.update({p: runtime[p] for p in runtime if runtime[p] != first[p]})
    return {
        "old": load(experiment / "panel-rounds/100/runtime-identity.json")["runtime_files"],
        "predecessor": first,
        "lifecycle_predecessor": baseline,
        "candidate": runtime,
        "allowed_source_deltas": allowed,
        "all_scientific_prompts_identical": True,
        "new_construction_repair_live_qualified": False,
        "new_creation_transport_live_qualified": False,
        "new_creation_provider_boundary_verified": True,
    }


def check_source(admission, name, expected):
    actual = admission["candidate"][name]
    if actual == expected:
        return "exact_previous_proof_bytes"
    assert expected in {
        admission[key].get(name) for key in ("old", "predecessor", "lifecycle_predecessor")
    }, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
