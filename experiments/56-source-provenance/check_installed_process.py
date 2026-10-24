"""Join real pip metadata/replacement with actual pytest-process observation.

Only our preserved toy packages; no biological inputs or native pipeline change.
The same Python3.13 pytest library is provided to the fixture interpreter; this
is explicitly fixture harness setup, not an AnnData environment repair.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
TOOLS = BASE.parents[2] / "pipeline54/.venv"
FIXTURE = BASE / "inputs-private/local-probe-002"


def inventory():
    return {
        str(p.relative_to(FIXTURE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(FIXTURE.rglob("*"))
        if p.is_file()
    }


def main():
    before = inventory()
    scratch = BASE / "inputs-private/installed-process-001"
    scratch.mkdir(exist_ok=False)
    commands, pairs = [], []
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONPATH=str(BASE),
        TMPDIR=str(scratch / "tmp"),
        UV_CACHE_DIR=str(scratch / "uv-cache"),
    )
    (scratch / "tmp").mkdir()

    def command(args, expected=0):
        result = subprocess.run(
            [str(x) for x in args],
            env=env,
            cwd=scratch,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        record = {
            "command": [str(x) for x in args],
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        commands.append(record)
        assert result.returncode == expected, record
        return record

    try:
        command([TOOLS / "bin/uv", "venv", "--python", sys.executable, scratch / "venv"])
        python = scratch / "venv/bin/python"
        pip = ["/home/exedev/miniforge3/bin/python3.13", "-m", "pip", "--python", python]
        command(
            [
                *pip,
                "install",
                "--no-index",
                "--no-build-isolation",
                "--no-deps",
                "-e",
                FIXTURE / "checkout",
            ]
        )
        test = scratch / "test_actual_install.py"
        test.write_text(
            "import biotasks56_target\ndef test_checkout():\n assert biotasks56_target.ORIGIN == 'checkout'\n"
        )
        for replaced in [False, True]:
            if replaced:
                command(
                    [
                        *pip,
                        "install",
                        "--no-index",
                        "--find-links",
                        FIXTURE / "wheels",
                        FIXTURE / "wheels/biotasks56_companion-1.0.0-py3-none-any.whl",
                    ]
                )
            pair = []
            for candidate in [False, True]:
                report = scratch / f"report-{replaced}-{candidate}.json"
                args = ["-q", "--import-mode=importlib", "-p", "no:cacheprovider", str(test)]
                if candidate:
                    args += [
                        "-p",
                        "provenance_plugin",
                        "--bt-origin-root",
                        str(FIXTURE / "checkout"),
                        "--bt-origin-project",
                        "biotasks56-target",
                        "--bt-origin-module",
                        "biotasks56_target",
                        "--bt-origin-report",
                        str(report),
                    ]
                launcher = (
                    "import sys;sys.path.append("
                    + repr(str(TOOLS / "lib/python3.13/site-packages"))
                    + ");import pytest;raise SystemExit(pytest.main(sys.argv[1:]))"
                )
                record = command(
                    [python, "-B", "-c", launcher, *args], expected=1 if replaced else 0
                )
                if candidate:
                    record["report"] = json.loads(report.read_text())
                pair.append(record)
            assert pair[0]["exit"] == pair[1]["exit"]
            assert ("1 failed" if replaced else "1 passed") in pair[0]["stdout"]
            assert ("1 failed" if replaced else "1 passed") in pair[1]["stdout"]
            events = pair[1]["report"]["events"]
            assert events[0]["pid"] == events[1]["pid"]
            for event in events:
                assert event["distribution"]["version"] == ("1.0.0" if replaced else "0.0.0")
                assert event["distribution"]["editable"] is not replaced
                assert event["modules"][0]["origin"] == ("foreign" if replaced else "checkout")
                assert event["targets_imported_by_observer"] is False
            pairs.append({"replaced": replaced, "baseline": pair[0], "candidate": pair[1]})
    finally:
        shutil.rmtree(scratch)
    assert inventory() == before, "Original preserved toy sources/wheels changed"
    result = {
        "synthetic": True,
        "real_pip_installation_and_pytest": True,
        "pytest_processes": 4,
        "baseline_candidate_outcomes_equal": True,
        "replacement_test_failure_preserved": True,
        "pairs": pairs,
        "setup_commands": commands,
        "source_inventory": before,
        "source_inventory_unchanged": True,
        "scratch_removed": not scratch.exists(),
        "native_or_model_calls": 0,
        "anndata_transaction_proven": False,
        "fixture_harness": "Same Python3.13 pytest library path appended to child interpreter for both baseline/candidate; no target module path added",
    }
    (BASE / "installed-process-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"pairs", "setup_commands", "source_inventory"}
            }
        )
    )


if __name__ == "__main__":
    main()
