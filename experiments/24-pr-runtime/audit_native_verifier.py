"""Exercise the pinned native verifier on synthetic logs, without task execution."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_SHA256 = "154ce5cbff54463ad7c08756abd22d198e17bd7ae3ff6ccdf994f5bf16ad021b"
ROOT = Path(__file__).resolve().parent
FIX = "tests/test_example.py::test_fix"
REGRESSION = "tests/test_example.py::test_existing"
OTHER = "tests/test_example.py::test_other"


def main(source):
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    spec = importlib.util.spec_from_file_location("native_verifier", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clean = f"{FIX} PASSED\n{REGRESSION} PASSED\n"
    cases = [
        ("all_tracked_pass", clean, 0, [FIX], [REGRESSION], True),
        ("base_failure", f"{FIX} FAILED\n{REGRESSION} PASSED\n", 1,
         [FIX], [REGRESSION], False),
        ("unparseable_exit_zero", "test wrapper exited without reporting tests\n",
         0, [FIX], [REGRESSION], False),
        ("missing_regression", f"{FIX} PASSED\n", 0, [FIX], [REGRESSION], False),
        ("untracked_failure", clean + f"{OTHER} FAILED\n", 1,
         [FIX], [REGRESSION], False),
        ("untracked_error_exit_zero", clean + f"{OTHER} ERROR\n", 0,
         [FIX], [REGRESSION], False),
        ("missing_f2p_oracle", clean, 0, [], [REGRESSION], False),
        ("no_retained_regression", f"{FIX} PASSED\n", 0, [FIX], [], False),
        ("command_failure_after_passes", clean, 2, [FIX], [REGRESSION], False),
    ]
    records = []
    with tempfile.TemporaryDirectory(prefix="biotasks24-verifier-") as directory:
        root = Path(directory)
        for name, log, exit_code, f2p, p2p, expected in cases:
            case = root / name
            case.mkdir()
            (case / "log.txt").write_text(log)
            (case / "f2p.json").write_text(json.dumps(f2p))
            (case / "p2p.json").write_text(json.dumps(p2p))
            process = subprocess.run([
                sys.executable, str(source), "--log", str(case / "log.txt"),
                "--f2p", str(case / "f2p.json"), "--p2p", str(case / "p2p.json"),
                "--test-cmds", "pytest -vv", "--exit-code", str(exit_code),
                "--out-dir", str(case),
            ], capture_output=True, text=True, timeout=10, check=True)
            details = json.loads((case / "reward-details.json").read_text())
            statuses = module.parse_logs("pytest", log)
            # This proposed reference-result gate is deliberately separate from
            # native reward. It does not prove provenance, baseline validity,
            # semantic agreement, environment reproducibility or task isolation.
            gate = bool(
                f2p and p2p and exit_code == 0
                and details.get("parse_status") == "ok"
                and details.get("command_resolved") is True
                and all(statuses.get(t) == "PASSED" for t in f2p + p2p)
                and not any(s in {"FAILED", "ERROR"} for s in statuses.values())
            )
            assert gate == expected, name
            records.append({
                "name": name, "input_log": log, "input_exit_code": exit_code,
                "f2p": f2p, "p2p": p2p, "native_details": details,
                "native_process_exit_code": process.returncode,
                "proposed_reference_gate": gate, "expected_reference_gate": expected,
            })
    output = {
        "evidence_kind": "synthetic verifier contract audit; no repository task run",
        "native_revision": "27d04ee8203cd5b2f20c3997d13836e5f5b64238",
        "native_source_sha256": SOURCE_SHA256,
        "cases": records,
        "limitations": [
            "Passing this gate is only one necessary condition for task acceptance.",
            "Synthetic log inputs do not establish honest or complete runner output.",
            "No build, Docker execution, real PR validation or solver run occurred.",
        ],
    }
    destination = ROOT / "evidence/native-verifier-audit.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({
        "cases": len(records),
        "native_reward_one_but_gate_rejects": [
            r["name"] for r in records
            if r["native_details"]["reward"] == 1 and not r["proposed_reference_gate"]
        ],
        "output": str(destination.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", required=True, type=Path)
    main(parser.parse_args().native_source.resolve())
