"""Controller for blind validation recomputation inside the existing sandbox."""

import json
import shutil
from pathlib import Path

from grading_remote import PRIVATE, PROBE, hashes, owned, run_as


def main():
    request = json.loads((PRIVATE / "alternative-request.json").read_text())
    inputs = Path("/work/task-inputs")
    before = hashes(inputs)
    case = Path("/work/probe/solution-case")
    shutil.rmtree(case, ignore_errors=True)
    owned(case, PROBE, 0o700)
    program = case / "solve.py"
    program.write_text(request["code"])
    program.chmod(0o444)
    owned(case / "outputs", PROBE, 0o700)
    result = run_as(
        PROBE,
        [
            "/work/venv/bin/python",
            str(program),
            "--input-dir",
            str(inputs),
            "--output-dir",
            str(case / "outputs"),
        ],
        case,
        request["seconds"],
    )
    record = {"status": "incomplete", "execution": result}
    if hashes(inputs) != before:
        raise ValueError("Independent solution changed task inputs")
    if result["exit_code"] != 0:
        return record
    after = hashes(case / "outputs")
    if set(after) != set(request["output_paths"]):
        raise ValueError("Independent solution output inventory mismatch")
    saved = PRIVATE / "alternative"
    shutil.rmtree(saved, ignore_errors=True)
    shutil.copytree(case / "outputs", saved)
    record["outputs"] = [
        dict(path=name, sha256=digest, bytes=(saved / name).stat().st_size)
        for name, digest in after.items()
    ]
    record["status"] = "executed_without_answer_access"
    return record


if __name__ == "__main__":
    print(json.dumps(main()))
