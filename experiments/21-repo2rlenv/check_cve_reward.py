import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
e = root / "evidence/biopython-cve-01"
task = next((e / "native/tasks").iterdir())
v = json.loads((e / "native/validation.json").read_text())
out = e / "verifier-checks"
out.mkdir(exist_ok=True)
records = []
for name, log, exit_code in [
    ("before_fix", v["pre_log"], 1),
    ("after_fix", v["post_log"], 0),
    ("no_test_evidence_success", "No tests executed.\n", 0),
]:
    d = out / name
    d.mkdir(exist_ok=True)
    (d / "input.log").write_text(log)
    command = [
        sys.executable,
        str(task / "tests/verifier.py"),
        "--log",
        str(d / "input.log"),
        "--f2p",
        str(task / "tests/f2p.json"),
        "--p2p",
        str(task / "tests/p2p.json"),
        "--test-cmds",
        "python -m pytest",
        "--exit-code",
        str(exit_code),
        "--out-dir",
        str(d),
    ]
    r = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0
    detail = json.loads((d / "reward-details.json").read_text())
    records.append({"case": name, **detail})
(out / "summary.json").write_text(
    json.dumps(
        {
            "stage": "offline_exported_verifier_check",
            "target_code_executed": False,
            "model_calls": 0,
            "note": "Original before/after native logs replayed with explicit test exit statuses; third input is synthetic absence of test evidence with exit 0, not an executed solver exploit.",
            "records": records,
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        [
            {
                k: r.get(k)
                for k in ["case", "reward", "resolved", "parse_status", "eval_trustworthy"]
            }
            for r in records
        ]
    )
)
