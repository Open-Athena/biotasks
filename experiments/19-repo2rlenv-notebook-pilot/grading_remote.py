"""Controller code executed only inside Daytona; generated code is unprivileged."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

PRIVATE = Path("/work/grading-private")
CASE = Path("/case")
AUTHOR, GRADER, PROBE = 18001, 18002, 18003


def hashes(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not permitted in artifacts")
        if path.is_file():
            with path.open("rb") as stream:
                result[path.relative_to(root).as_posix()] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    return result


def owned(path, uid, mode):
    path.mkdir(parents=True, exist_ok=True)
    os.chown(path, uid, uid)
    path.chmod(mode)


def run_as(uid, argv, cwd, seconds):
    def drop():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
        os.umask(0o077)

    # No model/provider credentials or controller context enter child execution.
    env = {
        "PATH": "/work/venv/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(cwd),
        "USER": "worker",
        "LANG": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        **{
            k: os.environ.get(k, "1")
            for k in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "POLARS_MAX_THREADS",
                "RAYON_NUM_THREADS",
            )
        },
    }
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        preexec_fn=drop,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def interrupted(_signal, _frame):
        raise TimeoutError("Outer controller interrupted generated execution")

    previous_handler = signal.signal(signal.SIGTERM, interrupted)
    try:
        stdout, stderr = process.communicate(timeout=seconds)
        return {"exit_code": process.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {
            "exit_code": None,
            "timed_out": True,
            "stdout": "",
            "stderr": "Generated process exceeded its timeout",
        }
    finally:
        # A tool may fork children; clean the entire owned group even on success.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        signal.signal(signal.SIGTERM, previous_handler)


def prepare(kind, omitted=None):
    shutil.rmtree(CASE, ignore_errors=True)
    CASE.mkdir(mode=0o755)
    shutil.copytree(PRIVATE / "oracle", CASE / "reference")
    (CASE / "reference").chmod(0o755)
    if kind == "empty":
        (CASE / "submission").mkdir()
    else:
        origin = (
            "recomputed"
            if kind == "recomputed"
            else "alternative"
            if kind == "alternative"
            else "oracle"
        )
        shutil.copytree(PRIVATE / origin, CASE / "submission")
    if omitted:
        (CASE / "submission" / omitted).unlink()
    for directory in (CASE / "reference", CASE / "submission"):
        for p in [directory, *directory.rglob("*")]:
            p.chmod(0o755 if p.is_dir() else 0o444)
    return hashes(CASE / "submission")


def main():
    mode = sys.argv[1]
    if mode == "initialize":
        PRIVATE.mkdir(exist_ok=True)
        PRIVATE.chmod(0o700)
        owned(Path("/work/author"), AUTHOR, 0o700)
        owned(Path("/work/probe"), PROBE, 0o700)
        return
    if mode == "shell":
        uid = AUTHOR if sys.argv[2] == "author" else PROBE
        cwd = Path("/work/author" if uid == AUTHOR else "/work/probe")
        print(json.dumps(run_as(uid, ["sh", "-c", sys.argv[3]], cwd, int(sys.argv[4]))))
        return
    request = json.loads((PRIVATE / "request.json").read_text())
    expected = json.loads((PRIVATE / "expected.json").read_text())
    if hashes(PRIVATE / "oracle") != expected:
        raise ValueError("Private reference was modified")
    before = prepare(request["kind"], request.get("omit"))
    record = {"status": "incomplete", "submission_before": before}
    if request["kind"] == "probe":
        # The probe cannot see the grader or other cases; only copied outputs.
        for p in [CASE / "submission", *(CASE / "submission").rglob("*")]:
            os.chown(p, PROBE, PROBE)
            p.chmod(0o700 if p.is_dir() else 0o600)
        (CASE / "probe.py").write_text(request["script"])
        (CASE / "probe.py").chmod(0o444)
        record["probe"] = run_as(
            PROBE,
            ["/work/venv/bin/python", str(CASE / "probe.py")],
            CASE / "submission",
            request["seconds"],
        )
        after = hashes(CASE / "submission")
        record["submission_after_probe"] = after
        record["probe_valid_execution"] = (
            record["probe"]["exit_code"] == 0
            and before != after
            and all(p in after for p in expected)
        )
        if not record["probe_valid_execution"]:
            print(json.dumps(record))
            return
    for p in [CASE / "submission", *(CASE / "submission").rglob("*")]:
        os.chown(p, 0, 0)
        p.chmod(0o755 if p.is_dir() else 0o444)
    submission = hashes(CASE / "submission")
    shutil.copyfile(PRIVATE / "grade.py", CASE / "grade.py")
    (CASE / "grade.py").chmod(0o444)
    owned(CASE / "result", GRADER, 0o700)
    record["grader"] = run_as(
        GRADER,
        [
            "/work/venv/bin/python",
            str(CASE / "grade.py"),
            "--reference-dir",
            str(CASE / "reference"),
            "--submission-dir",
            str(CASE / "submission"),
            "--report",
            str(CASE / "result/report.json"),
        ],
        CASE,
        request["seconds"],
    )
    report = CASE / "result/report.json"
    if report.is_file() and not report.is_symlink():
        try:
            record["report"] = json.loads(report.read_text())
        except (ValueError, OSError) as error:
            record["report_error"] = type(error).__name__
    if (
        hashes(CASE / "reference") != expected
        or hashes(CASE / "submission") != submission
        or hashes(PRIVATE / "oracle") != expected
    ):
        raise ValueError("Grader changed read-only scientific artifacts")
    record["status"] = "executed"
    record["submission_sha256"] = submission
    print(json.dumps(record))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {"status": "incomplete", "error_type": type(error).__name__, "error": str(error)}
            )
        )
