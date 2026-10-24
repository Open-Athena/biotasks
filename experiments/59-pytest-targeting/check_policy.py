"""Run original/candidate commands with real pytest in our isolated layouts."""

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from policy import wrap

BASE = Path(__file__).parent.resolve()
loader_path = BASE.parents[2] / "58/experiments/58-assertion-regressions/check_filter.py"
spec = importlib.util.spec_from_file_location("original58_functions", loader_path)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
functions, parse_pytest = loader.load_functions()
original = functions["targeted_test_cmds_for_pr"]


def main():
    scratch = BASE / "inputs-private/policy-001"
    scratch.mkdir(exist_ok=False)
    results = []
    try:
        cases = [
            ("root", ".", ["Tests/test_a.py"], ""),
            ("nested", "Tests", ["Tests/test_a.py"], ""),
            ("nested_multiple", "Tests", ["Tests/test_a.py", "Tests/test_b.py"], ""),
            ("quoted_new_target", ".", ["Tests/test with space.py"], ""),
            ("quoted_cwd", "Tests with space", ["Tests with space/test_a.py"], ""),
            ("existing_target", "Tests", ["Tests/test_b.py"], " test_a.py"),
            ("existing_quoted_target", "Tests", ["Tests/test_b.py"], " 'test with space.py'"),
            ("existing_node_id", "Tests", ["Tests/test_b.py"], " test_a.py::test_value"),
        ]
        for name, cwd, files, existing in cases:
            directory = scratch / name
            for folder in ["Tests", "Tests with space"]:
                (directory / folder).mkdir(parents=True)
                for file in ["test_a.py", "test_b.py", "test with space.py"]:
                    (directory / folder / file).write_text("def test_value():\n assert True\n")
            command = (
                "cd "
                + shlex.quote(str(directory / cwd))
                + " && "
                + shlex.quote(sys.executable)
                + " -B -m pytest -v -p no:cacheprovider --junitxml=out.xml"
                + existing
            )
            candidate = wrap(original, str(directory))
            outputs = []
            for kind, transformed in [
                ("original", original([command], files)),
                ("candidate", candidate([command], files)),
            ]:
                assert len(transformed) == 1
                result = subprocess.run(
                    ["bash", "-c", transformed[0]],
                    cwd=directory,
                    env=dict(
                        os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1"
                    ),
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                xml = directory / cwd / "out.xml"
                assert xml.is_file(), result.stdout + result.stderr
                cases_xml = [
                    (
                        x.attrib.get("classname"),
                        x.attrib["name"],
                        "failed"
                        if x.find("failure") is not None
                        else "error"
                        if x.find("error") is not None
                        else "passed",
                    )
                    for x in ET.parse(xml).iter("testcase")
                ]
                xml.unlink()
                outputs.append(
                    {
                        "route": kind,
                        "command": transformed[0],
                        "exit": result.returncode,
                        "testcases_junit": cases_xml,
                        "parsed_original_pytest": parse_pytest(result.stdout),
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
            a, b = outputs
            assert b["exit"] == 0 and b["testcases_junit"], outputs
            if name in {"root", "existing_target"}:
                assert a["exit"] == b["exit"] == 0
                assert a["testcases_junit"] == b["testcases_junit"]
                assert a["parsed_original_pytest"] == b["parsed_original_pytest"]
            if name in {"nested", "nested_multiple", "quoted_new_target", "quoted_cwd"}:
                assert a["exit"] == 4, outputs
            if existing:
                assert candidate([command], files) == [command]
                assert len(b["testcases_junit"]) == 1
            results.append({"case": name, "original": a, "candidate": b})
        candidate = wrap(original)
        for command, files in [
            ("go test ./...", ["pkg/one_test.go"]),
            ("cargo test", ["src/lib.rs"]),
            ("npx jest", ["tests/a.test.js"]),
        ]:
            assert candidate([command], files) == original([command], files)
        rejected = []
        for path in ["../outside.py", "Tests/../outside.py", "/outside.py", "bad\0.py"]:
            try:
                candidate(["pytest -v"], [path])
            except ValueError:
                rejected.append(repr(path))
            else:
                raise AssertionError(path)
        try:
            wrap(lambda commands, files: ["unexpected-source-change"])(
                ["pytest"], ["Tests/test_a.py"]
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Changed source behavior must reject")
    finally:
        shutil.rmtree(scratch)
    value = {
        "synthetic": True,
        "real_pytest_processes": len(results) * 2,
        "cases": results,
        "rejected_paths": rejected,
        "non_pytest_original_behavior_unchanged": True,
        "changed_source_behavior_rejected": True,
        "scratch_removed": not scratch.exists(),
        "native_jobs_or_model_calls": 0,
        "native_deployed": False,
        "limits": "Recognized Python targets only; original runner detection and option-value ambiguity remain. JUnit is an independent fixture observation, not a native reward or parser repair.",
    }
    (BASE / "policy-proof.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({k: v for k, v in value.items() if k != "cases"}))


if __name__ == "__main__":
    main()
