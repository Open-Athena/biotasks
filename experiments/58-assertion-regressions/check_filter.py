"""Use pinned upstream pure functions and parser with our real pytest fixtures.

No biology import, native job, model call, original patch/test or reward repair.
AST selection avoids importing unrelated upstream runtime/agent dependencies.
"""

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).parent.resolve()
SOURCE = (
    BASE.parents[2]
    / "48/experiments/48-generation-manifest/inputs-private/installed-proof-004/source-cache/source"
)


def load_functions():
    binding = json.loads((BASE / "source-binding.json").read_text())
    for row in binding["files"]:
        assert hashlib.sha256((SOURCE / row["path"]).read_bytes()).hexdigest() == row["sha256"]
    source = SOURCE / "src/repo2rlenv/pipelines/pr_runtime.py"
    tree = ast.parse(source.read_text())
    wanted = {
        "_DIFF_HEADER_RE",
        "_NEW_TEST_FUNC_RE",
        "_PYTEST_TARGETABLE_EXT",
        "_JEST_TARGETABLE_EXT",
        "_files_in_patch",
        "_count_new_test_funcs",
        "normalize_test_cmds_for_runtime",
        "targeted_test_cmds_for_pr",
        "_go_packages_from_test_files",
    }
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(x, ast.Name) and x.id in wanted for x in node.targets
        ):
            nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "PRRuntimePipeline":
            nodes += [
                x
                for x in node.body
                if isinstance(x, ast.FunctionDef) and x.name == "_structural_quality_filter"
            ]
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    parser_path = SOURCE / "src/repo2rlenv/log_parsers/pytest_parser.py"
    parser = {}
    exec(compile(parser_path.read_text(), str(parser_path), "exec"), parser)
    return namespace, parser["parse_pytest"]


def diff(name, before, after):
    return (
        "diff --git a/"
        + name
        + " b/"
        + name
        + "\n"
        + "".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile="a/" + name,
                tofile="b/" + name,
            )
        )
    )


def main():
    functions, parse_pytest = load_functions()
    scratch = BASE / "inputs-private/filter-001"
    scratch.mkdir(exist_ok=False)
    records = []
    initial = "from bt58_target import value\ndef test_existing():\n assert value() >= 0\n"
    tests = {
        "assertion_in_existing": initial + " assert value() == 1\n",
        "new_function": initial + "\ndef test_regression():\n assert value() == 1\n",
        "cosmetic_only": initial + "# explanatory comment\n",
        "ci_only": initial + "\ndef test_regression():\n assert value() == 1\n",
    }
    try:
        for name, test in tests.items():
            test_patch = diff("test_regression.py", initial, test)
            source_patch = diff(
                ".github/workflows/check.yml" if name == "ci_only" else "bt58_target.py",
                "def value():\n return 0\n",
                "def value():\n return 1\n",
            )
            gates = {}
            for setting in [True, False]:
                self = SimpleNamespace(
                    options=SimpleNamespace(require_new_test_funcs=setting, skip_ci_only=True)
                )
                gates[str(setting)] = functions["_structural_quality_filter"](
                    self, source_patch, test_patch
                )
            expected = (
                "ci_only_patch"
                if name == "ci_only"
                else None
                if name == "new_function"
                else "no_new_test_funcs"
            )
            assert gates["True"] == expected
            assert gates["False"] == ("ci_only_patch" if name == "ci_only" else None)
            stages = []
            for post in [False, True]:
                directory = scratch / name / ("post" if post else "pre")
                directory.mkdir(parents=True)
                (directory / "bt58_target.py").write_text(
                    "def value():\n return " + ("1" if post else "0") + "\n"
                )
                (directory / "test_regression.py").write_text(test)
                command = [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-v",
                    "-p",
                    "no:cacheprovider",
                    "--rootdir=.",
                    "--confcutdir=.",
                    "test_regression.py",
                ]
                result = subprocess.run(
                    command,
                    cwd=directory,
                    env=dict(
                        os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1"
                    ),
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                statuses = parse_pytest(result.stdout)
                assert statuses, result.stdout + result.stderr
                stages.append(
                    {
                        "post": post,
                        "exit": result.returncode,
                        "statuses": statuses,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "command": command,
                    }
                )
            pre, post = [r["statuses"] for r in stages]
            f2p = sorted(k for k in pre if pre[k] == "FAILED" and post.get(k) == "PASSED")
            p2p = sorted(k for k in pre if pre[k] == post.get(k) == "PASSED")
            assert len(f2p) == (0 if name == "cosmetic_only" else 1)
            records.append(
                {
                    "case": name,
                    "new_test_function_count": functions["_count_new_test_funcs"](test_patch),
                    "default_gate": gates["True"],
                    "explicit_false_gate": gates["False"],
                    "f2p": f2p,
                    "p2p": p2p,
                    "real_pytest_stages": stages,
                    "eligible_is_not_native_validation_or_scientific_acceptance": True,
                }
            )
        baseline = json.loads((BASE / "baseline-bootstrap.json").read_text())
        targeted = functions["targeted_test_cmds_for_pr"](
            functions["normalize_test_cmds_for_runtime"](baseline["test_cmds"]),
            ["Tests/test_PDB_PDBIO.py"],
        )
        assert targeted == ["cd /workspace/Tests && python -m pytest -v Tests/test_PDB_PDBIO.py"]
        directory = scratch / "cwd_targeting"
        (directory / "Tests").mkdir(parents=True)
        (directory / "Tests/test_PDB_PDBIO.py").write_text("def test_example():\n assert True\n")
        env = dict(
            os.environ,
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTHONDONTWRITEBYTECODE="1",
            PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        )
        command = targeted[0].replace("/workspace", str(directory)) + " -p no:cacheprovider"
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 4 and not parse_pytest(result.stdout), (
            result.stdout + result.stderr
        )
        cwd = {
            "recorded_bootstrap_command": baseline["test_cmds"],
            "actual_upstream_targeted_command": targeted,
            "fixture_only_workspace_substitution": str(directory),
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "native_biopython_validation_run": False,
            "finding": "Original helper appends a root-relative file after cd into Tests; the synthetic faithful layout has no Tests/Tests path. This is a source/fixture prediction for Biopython, not a native outcome.",
        }
    finally:
        shutil.rmtree(scratch)
    value = {
        "synthetic": True,
        "real_pytest_processes": 9,
        "source_filter_and_original_parser_used": True,
        "cases": records,
        "targeting_preflight": cwd,
        "scratch_removed": not scratch.exists(),
        "new_model_native_calls": 0,
        "native_candidate_admitted": False,
        "limitation": "Pure filter helpers plus real standalone pytest/parser fixtures; not the full native validator, environment or reward.",
    }
    (BASE / "filter-proof.json").write_text(json.dumps(value, indent=2) + "\n")
    print(
        json.dumps(
            {
                "cases": len(records),
                "real_pytest_processes": 9,
                "cwd_targeting_exit": cwd["exit"],
                "scratch_removed": value["scratch_removed"],
                "native_model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
