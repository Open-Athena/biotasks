"""Admit the recorded general review/coverage prompts and input-restaging check.

Operator validation only: does not alter frozen scientific artifacts or label
historical live proofs as whole-pipeline qualification of this successor.
"""

import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
DELTAS = {
    PREFIX + "grading_protocol.py",
    PREFIX + "reference_setup.py",
    PREFIX + "test_reference_setup.py",
    "src/biotasks/prompts/notebook-grader-review.md",
    "src/biotasks/prompts/notebook-reference-prepare.md",
    "src/biotasks/prompts/notebook-reference-setup.md",
    "src/biotasks/prompts/notebook-specification-review.md",
    "src/biotasks/prompts/notebook-task-specification.md",
}
HOOK = """record["staging_reproducibility"] = await self.check_staging_reproducibility(directory, staged)
if staged["files"]:
    await self.audit_system_packages(recipe, directory, "after-restaging")
    _, _, after_restaging = await self.capture_candidate(directory / "after-restaging")
    if after_restaging != hashes:
        raise ValueError("Restaging changed its submitted candidate files")
"""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def prove_setup_addition_only(before, after):
    old, new = ast.parse(before), ast.parse(after)
    klass = next(
        node for node in new.body if isinstance(node, ast.ClassDef) and node.name == "SetupSession"
    )
    methods = [
        node
        for node in klass.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "check_staging_reproducibility"
    ]
    assert len(methods) == 1
    klass.body.remove(methods[0])
    test = next(
        node
        for node in klass.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "test_reference"
    )
    hook = ast.parse(HOOK).body
    removed = 0

    class StripHook(ast.NodeTransformer):
        def generic_visit(self, node):
            nonlocal removed
            for _, value in ast.iter_fields(node):
                if isinstance(value, list) and all(isinstance(item, ast.stmt) for item in value):
                    for start in range(max(0, len(value) - len(hook) + 1)):
                        if [ast.dump(item) for item in value[start : start + len(hook)]] == [
                            ast.dump(item) for item in hook
                        ]:
                            del value[start : start + len(hook)]
                            removed += 1
                            break
            return super().generic_visit(node)

    StripHook().visit(test)
    assert removed == 1
    assert ast.dump(old) == ast.dump(new), (
        "Unknown setup change beyond the isolated restaging method and audited hook"
    )


def candidate_admission(repo, runtime):
    repo = Path(repo)
    experiment = repo / PREFIX
    previous = load(experiment / "panel-rounds/103/runtime-identity.json")
    baseline = previous["runtime_files"]
    expected = load(experiment / "panel-rounds/104/candidate-runtime-identity.json")
    checks = load(experiment / "panel-rounds/104/offline-checks.json")
    assert runtime == expected["runtime_files"] and set(runtime) == set(baseline)
    assert {path for path in runtime if runtime[path] != baseline[path]} == DELTAS
    assert all(digest((repo / path).read_bytes()) == sha for path, sha in runtime.items())
    prior = load(experiment / "panel-rounds/103/source-admission.json")
    assert (
        digest((experiment / "panel-rounds/103/runtime_admission.py").read_bytes())
        == prior["admission_helper_sha256"]
    )
    assert (
        load(experiment / "factory-checks/session-create-conflict/candidate-runtime-identity.json")[
            "runtime_files"
        ]
        == baseline
    )
    assert (
        checks["affected_tests_passed"] == 149
        and checks["request_id_acceptance_equivalence_scenarios"] == 1080
    )
    for path, sha in checks["source_sha256"].items():
        assert runtime[path] == sha
    staging = checks["staging_reproducibility"]
    assert staging["tests"]["complete_affected_reference_group"]["passed"] == 171
    for path, sha in staging["source_sha256"].items():
        assert digest((repo / path).read_bytes()) == sha
    before = subprocess.check_output(
        ["git", "show", previous["public_runtime_revision"] + ":" + PREFIX + "reference_setup.py"],
        cwd=repo,
    )
    assert digest(before) == baseline[PREFIX + "reference_setup.py"]
    prove_setup_addition_only(before, (experiment / "reference_setup.py").read_bytes())
    source = experiment / "factory-checks/review-feedback/candidate.py"
    spec = importlib.util.spec_from_file_location("recorded_feedback_candidate", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path, (_, candidate) in module.proposed_changes().items():
        assert path.read_text() == candidate
    root = experiment / "factory-checks/staging-reproducibility"
    raw = (root / "live-check-configuration.json").read_bytes()
    config, proof = json.loads(raw), load(root / "integration-summary.json")
    clean_raw = (root / "live-fresh-provider-cleanup.json").read_bytes()
    clean = json.loads(clean_raw)
    assert proof["source_configuration_sha256"] == digest(raw) and proof[
        "fresh_cleanup_sha256"
    ] == digest(clean_raw)
    assert proof["status"] == "provider_boundary_observed_not_scientific_qualification"
    assert proof["new_model_calls"] == 0 and proof["scientific_computation"] is False
    assert {row["name"] for row in proof["cases"]} == {
        "stable",
        "volatile-metadata",
        "changed-data",
    }
    assert all(
        row["passed"]
        and row["strict_original_hash_gate_preserved"]
        and row["authoring_workspace_restored"]
        and row["scientific_dispatches"] == 0
        for row in proof["cases"]
    )
    assert all(
        clean[key] is True
        for key in (
            "complete",
            "fresh_original_id_absent",
            "fresh_owner_list_empty",
            "original_cleanup_verified",
        )
    )
    for path, sha in config["source_sha256"].items():
        assert digest((repo / path).read_bytes()) == sha
    original = load(experiment / "panel-rounds/101/source-admission.json")
    first = load(experiment / "panel-rounds/101/runtime-identity.json")["runtime_files"]
    allowed = dict(original["candidate_deltas"])
    allowed.update({path: runtime[path] for path in runtime if runtime[path] != first[path]})
    return {
        "old": load(experiment / "panel-rounds/100/runtime-identity.json")["runtime_files"],
        "predecessor": first,
        "lifecycle_predecessor": load(experiment / "panel-rounds/102/runtime-identity.json")[
            "runtime_files"
        ],
        "creation_predecessor": baseline,
        "candidate": runtime,
        "allowed_source_deltas": allowed,
        "all_scientific_prompts_identical": False,
        "new_construction_repair_live_qualified": False,
        "new_staging_provider_boundary_verified": True,
        "new_whole_pipeline_live_qualified": False,
    }


def check_source(admission, name, expected):
    actual = admission["candidate"][name]
    if actual == expected:
        return "exact_previous_proof_bytes"
    assert expected in {
        admission[key].get(name)
        for key in ("old", "predecessor", "lifecycle_predecessor", "creation_predecessor")
    }, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
