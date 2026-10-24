"""Infrastructure fixtures only. Execute inside an owned disposable root sandbox."""

import json
import shutil
import sys
from pathlib import Path

import grading_remote as remote


def main():
    root = Path("/work/trusted-input-check")
    root.mkdir(mode=0o755)
    source = root / "author-inputs"
    source.mkdir()
    (source / "entities.txt").write_text("alpha\nbeta\n")
    remote.PRIVATE = root / "private"
    remote.PRIVATE.mkdir(mode=0o700)
    remote.TRUSTED_INPUTS = root / "trusted"
    (remote.PRIVATE / "expected-inputs.json").write_text(json.dumps(remote.hashes(source)))
    Path("/work/venv/bin").mkdir(parents=True)
    Path("/work/venv/bin/python").symlink_to(sys.executable)
    remote.seal_inputs(source)
    cases = []
    observations = []
    for role in (remote.AUTHOR, remote.PROBE, remote.ORACLE, remote.GRADER):
        cwd = root / str(role)
        remote.owned(cwd, role, 0o700)
        result = remote.run_as(
            role,
            [
                sys.executable,
                "-c",
                "from pathlib import Path; "
                + f"print(Path({str(remote.TRUSTED_INPUTS / 'entities.txt')!r}).read_text())",
            ],
            cwd,
            10,
        )
        assert result["role_process_cleanup_verified"]
        assert (result["exit_code"] == 0) == (role == remote.GRADER)
        if role != remote.GRADER:
            assert "PermissionError" in result["stderr"]
        observations.append({"role": role, "exit_code": result["exit_code"]})
    denied = remote.run_as(
        remote.GRADER,
        [
            sys.executable,
            "-c",
            "import os; from pathlib import Path; "
            "(Path(os.environ['BIOTASKS_TRUSTED_INPUT_DIR'])/'entities.txt').write_text('bad')",
        ],
        root / str(remote.GRADER),
        10,
    )
    assert denied["exit_code"] != 0 and "PermissionError" in denied["stderr"]
    cases.append(
        {"name": "dedicated-role-read-and-write-permissions", "passed": True, "roles": observations}
    )

    (source / "entities.txt").write_text("invented\n")
    assert remote.trusted_input_directory() == remote.TRUSTED_INPUTS
    original = (remote.TRUSTED_INPUTS / "entities.txt").read_bytes()
    (remote.TRUSTED_INPUTS / "entities.txt").write_bytes(b"tampered\n")
    try:
        remote.trusted_input_directory()
    except ValueError:
        pass
    else:
        raise AssertionError("Controller failed to detect original-input tampering")
    (remote.TRUSTED_INPUTS / "entities.txt").write_bytes(original)
    remote.trusted_input_directory()
    cases.append({"name": "original-identity-and-mutable-copy-separation", "passed": True})

    tests, outputs, logs = [root / name for name in ("native-tests", "outputs", "logs")]
    for directory in (tests, outputs, logs):
        directory.mkdir()
    shutil.copytree(remote.TRUSTED_INPUTS, tests / "inputs")
    (tests / "inputs-manifest.json").write_text(json.dumps(remote.hashes(tests / "inputs")))
    (tests / "checks.json").write_text(json.dumps([{"id": "member", "kind": "scientific"}]))
    (tests / "outputs.json").write_text(json.dumps(["result.txt"]))
    (tests / "grade.py").write_text(
        "import argparse,json,os\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser()\n"
        "for k in ('reference-dir','submission-dir','report'):p.add_argument('--'+k)\n"
        "a=p.parse_args()\n"
        "i=Path(os.environ['BIOTASKS_TRUSTED_INPUT_DIR'])/'entities.txt'\n"
        "passed=(Path(a.submission_dir)/'result.txt').read_text() in i.read_text().splitlines()\n"
        "Path(a.report).write_text(json.dumps({'passed':passed,'checks':[{'id':'member','passed':passed}]}))\n"
    )
    wrapper = Path("/work/verify-template.py").read_text()
    wrapper = (
        wrapper.replace("/workspace/outputs", str(outputs))
        .replace("/logs/verifier", str(logs))
        .replace("/tests", str(tests))
    )
    observations = []
    for value, expected in (("alpha", "1"), ("beta", "1"), ("invented", "0")):
        (outputs / "result.txt").write_text(value)
        exec(compile(wrapper, "native-verifier.py", "exec"), {"__name__": "__main__"})
        assert (logs / "reward.txt").read_text().strip() == expected
        observations.append({"fixture_value": value, "reward": expected})
    cases.append(
        {"name": "native-wrapper-original-input-parity", "passed": True, "results": observations}
    )
    print(
        json.dumps(
            {"cases": cases, "synthetic": True, "model_calls": 0, "scientific_computation": False}
        )
    )


if __name__ == "__main__":
    main()
