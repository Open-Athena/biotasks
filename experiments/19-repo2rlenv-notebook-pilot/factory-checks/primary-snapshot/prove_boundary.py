"""Prove a final-transport-only candidate against the frozen ten-source runtime."""

import argparse
import ast
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

BASE = "2a8392be"
PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
EXPERIMENT = Path(__file__).resolve().parents[2]
REPO = EXPERIMENT.parents[1]


def original(name):
    return subprocess.check_output(["git", "show", BASE + ":" + PREFIX + name], cwd=REPO)


def same(left, right):
    assert ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def prove_bootstrap(before, after):
    old, new = ast.parse(before), ast.parse(after)
    old_functions = {node.name: node for node in old.body if isinstance(node, ast.FunctionDef)}
    functions = {node.name: node for node in new.body if isinstance(node, ast.FunctionDef)}
    for name in ("export_on_host", "snapshot", "restore_snapshot"):
        assert ast.get_docstring(functions[name]) is not None
        functions[name].body[0] = old_functions[name].body[0]
    signature = functions["export_on_host"].args
    assert signature.kwonlyargs[-1].arg == "snapshot"
    assert isinstance(signature.kw_defaults[-1], ast.Constant)
    assert signature.kw_defaults[-1].value is False
    signature.kwonlyargs.pop()
    signature.kw_defaults.pop()

    class Mode(ast.NodeTransformer):
        changed = 0

        def visit_IfExp(self, node):
            if isinstance(node.test, ast.Name) and node.test.id == "snapshot":
                assert isinstance(node.body, ast.Constant) and node.body.value == "--snapshot"
                assert isinstance(node.orelse, ast.Constant) and node.orelse.value == "--export"
                self.changed += 1
                return node.orelse
            return self.generic_visit(node)

    mode = Mode()
    mode.visit(new)
    assert mode.changed == 1
    same(old, new)


def prove_controller(before, after):
    old, new = ast.parse(before), ast.parse(after)
    calls = [
        node
        for node in ast.walk(new)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "asyncio"
        and node.func.attr == "to_thread"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "export_on_host"
    ]
    assert len(calls) == 1
    call = calls[0]
    assert len(call.args) == 3 and isinstance(call.args[2], ast.BinOp)
    assert isinstance(call.args[2].right, ast.Constant)
    assert call.args[2].right.value == "/autonomous-snapshot"
    call.args[2].right.value = "/autonomous"
    flags = [item for item in call.keywords if item.arg == "snapshot"]
    assert len(flags) == 1
    assert isinstance(flags[0].value, ast.Constant) and flags[0].value.value is True
    call.keywords.remove(flags[0])
    same(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    assert not args.proof.exists()
    paths = ("iris_bootstrap.py", "run_autonomous.py")
    for name, check in zip(paths, (prove_bootstrap, prove_controller), strict=True):
        check(original(name), (EXPERIMENT / name).read_bytes())
    runtime = json.loads((EXPERIMENT / "panel-rounds/108/runtime-identity-224.json").read_text())[
        "runtime_files"
    ]
    current = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in runtime}
    changed = sorted(name for name in runtime if current[name] != runtime[name])
    assert changed == sorted(
        PREFIX + name for name in (*paths, "test_evidence_export.py", "test_autonomous.py")
    )
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "base_revision": subprocess.check_output(
            ["git", "rev-parse", BASE], cwd=REPO, text=True
        ).strip(),
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime_files": len(runtime),
        "runtime_changes": {
            name: {"before": runtime[name], "after": current[name]} for name in changed
        },
        "all_other_runtime_hashes_identical": True,
        "controller_only_final_export_mode_and_prefix_changed": True,
        "bootstrap_only_optional_mode_and_docs_changed": True,
        "scientific_reward_resource_model_deadline_repair_policy_ast_unchanged": True,
        "candidate_adopted_or_launched": False,
        "live_provider_validation": False,
        "new_jobs_or_model_calls": 0,
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
