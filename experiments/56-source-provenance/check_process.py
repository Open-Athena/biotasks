"""Real pytest baseline/candidate comparison over our own small source fixtures."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
CASES = {
    "checkout": (
        "checkout",
        "import bt56_module\ndef test_value():\n assert bt56_module.value() == 1\n",
    ),
    "foreign": (
        "foreign",
        "import bt56_module\ndef test_value():\n assert bt56_module.value() == 1\n",
    ),
    "symlink_to_checkout": (
        "symlink",
        "import bt56_module\ndef test_value():\n assert bt56_module.value() == 1\n",
    ),
    "stale_loaded_code": (
        "checkout",
        'import bt56_module\nfrom pathlib import Path\ndef test_value():\n p=Path(bt56_module.__file__)\n p.write_text(p.read_text().replace("return 1", "return 2"))\n assert bt56_module.value() == 1\n',
    ),
    "runtime_import": (
        "checkout",
        "def test_value():\n import bt56_module\n assert bt56_module.value() == 1\n",
    ),
    "namespace": (
        "namespace",
        "import bt56_module\ndef test_value():\n assert bt56_module.__file__ is None\n",
    ),
    "unobserved": ("unobserved", "def test_value():\n assert True\n"),
    "original_failure": (
        "checkout",
        "import bt56_module\ndef test_value():\n assert bt56_module.value() == 2\n",
    ),
}


def run():
    scratch = BASE / "inputs-private" / "process-001"
    scratch.mkdir(exist_ok=False)
    records = []
    try:
        for name, (kind, source) in CASES.items():
            pair = []
            for instrumented in [False, True]:
                directory = scratch / name / ("candidate" if instrumented else "baseline")
                checkout, foreign = directory / "checkout", directory / "foreign"
                checkout.mkdir(parents=True)
                foreign.mkdir()
                module_source = "def value():\n return 1\n"
                (checkout / "bt56_module.py").write_text(module_source)
                (foreign / "bt56_module.py").write_text(module_source)
                if kind == "symlink":
                    (foreign / "bt56_module.py").unlink()
                    (foreign / "bt56_module.py").symlink_to(checkout / "bt56_module.py")
                if kind == "namespace":
                    (checkout / "bt56_module.py").unlink()
                    (checkout / "bt56_module").mkdir()
                if kind == "unobserved":
                    (checkout / "bt56_module.py").write_text(
                        "raise RuntimeError('must not be imported')\n"
                    )
                test = directory / "test_synthetic.py"
                test.write_text(source)
                selected = foreign if kind in {"foreign", "symlink"} else checkout
                env = dict(
                    os.environ,
                    PYTHONPATH=os.pathsep.join([str(BASE), str(selected)]),
                    PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                    PYTHONDONTWRITEBYTECODE="1",
                )
                report = directory / "provenance.json"
                command = [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "--import-mode=importlib",
                    "-p",
                    "no:cacheprovider",
                    str(test),
                ]
                if instrumented:
                    command.extend(
                        [
                            "-p",
                            "provenance_plugin",
                            "--bt-origin-root",
                            str(checkout),
                            "--bt-origin-project",
                            "biotasks56-synthetic-uninstalled",
                            "--bt-origin-module",
                            "bt56_module",
                            "--bt-origin-report",
                            str(report),
                        ]
                    )
                result = subprocess.run(
                    command,
                    cwd=directory,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                summary = re.findall(r"\b(\d+) (passed|failed|error|skipped)\b", result.stdout)
                record = {
                    "instrumented": instrumented,
                    "command": command,
                    "exit": result.returncode,
                    "summary": summary,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "test_sha256": hashlib.sha256(test.read_bytes()).hexdigest(),
                }
                if instrumented:
                    assert report.is_file(), record
                    record["report"] = json.loads(report.read_text())
                pair.append(record)
            a, b = pair
            assert a["exit"] == b["exit"] == (1 if name == "original_failure" else 0), pair
            assert a["summary"] == b["summary"] and a["summary"], pair
            assert a["test_sha256"] == b["test_sha256"]
            events = b["report"]["events"]
            assert len(events) == 2 and events[0]["pid"] == events[1]["pid"]
            assert all(not event["targets_imported_by_observer"] for event in events)
            collection, final = [event["modules"][0] for event in events]
            expected = {
                "foreign": "foreign",
                "namespace": "ambiguous",
                "unobserved": "unobserved",
            }.get(name, "checkout")
            assert final["origin"] == expected, b
            if name == "stale_loaded_code":
                assert collection["function_comparison"] == "matches_observed_functions"
                assert final["function_comparison"] == "mismatch"
            elif name == "runtime_import":
                assert collection["origin"] == "unobserved"
                assert final["function_comparison"] == "matches_observed_functions"
            elif expected in {"checkout", "foreign"}:
                assert final["function_comparison"] == "matches_observed_functions"
            records.append({"case": name, "baseline": a, "candidate": b})
    finally:
        shutil.rmtree(scratch)
    result = {
        "synthetic": True,
        "real_pytest_processes": len(records) * 2,
        "cases_passed": len(records),
        "baseline_candidate_exit_and_counts_equal": True,
        "records": records,
        "scratch_removed": not scratch.exists(),
        "new_native_jobs": 0,
        "new_model_calls": 0,
        "native_biology_execution": False,
        "accepted_task_or_grading_claim": False,
    }
    (BASE / "process-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}))


if __name__ == "__main__":
    run()
