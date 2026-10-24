"""Controller code executed only inside Daytona; generated code is unprivileged."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PRIVATE = Path("/work/grading-private")
TRUSTED_INPUTS = Path("/work/grader-inputs")
CASE = Path("/case")
AUTHOR, GRADER, PROBE, ORACLE = 18001, 18002, 18003, 18004
WORKER_ROLES = frozenset({AUTHOR, GRADER, PROBE, ORACLE})


def role_processes(uid, proc=Path("/proc")):
    """Find live processes for a dedicated role inside this disposable sandbox.

    UIDs are reserved by the controller for one foreground call at a time. A
    descendant may start a new process group or session; ancestry/group-only
    cleanup cannot prove that the role has stopped. Never use a shared-node UID.
    """
    if uid not in WORKER_ROLES:
        raise ValueError("Only dedicated sandbox worker roles may be inspected")
    result = []
    for path in proc.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = dict(line.split(":", 1) for line in (path / "status").read_text().splitlines())
        except (FileNotFoundError, ProcessLookupError):
            continue
        if uid in map(int, fields["Uid"].split()) and fields["State"].split()[0] != "Z":
            result.append(int(path.name))
    return result


def stop_role_processes(uid):
    if uid not in WORKER_ROLES or os.geteuid() != 0:
        raise RuntimeError("Role cleanup requires the disposable sandbox root controller")
    deadline = time.monotonic() + 2
    while pids := role_processes(uid):
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if time.monotonic() >= deadline:
            raise RuntimeError("Worker process cleanup could not be verified")
        time.sleep(0.02)


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


def trusted_input_directory():
    """Check the controller's original input identities, never submission copies."""
    manifest = PRIVATE / "expected-inputs.json"
    if not manifest.exists():
        return None
    expected = json.loads(manifest.read_text())
    if TRUSTED_INPUTS.is_symlink() or not TRUSTED_INPUTS.is_dir():
        raise ValueError("Trusted task input directory is missing or unsafe")
    if hashes(TRUSTED_INPUTS) != expected:
        raise ValueError("Trusted task inputs differ from their original identities")
    return TRUSTED_INPUTS


def seal_inputs(source):
    """Give only the grader role read access to a separately sealed input copy."""
    expected = json.loads((PRIVATE / "expected-inputs.json").read_text())
    if hashes(source) != expected:
        raise ValueError("Task inputs changed before verifier staging")
    shutil.copytree(source, TRUSTED_INPUTS)
    for path in [TRUSTED_INPUTS, *TRUSTED_INPUTS.rglob("*")]:
        os.chown(path, 0, GRADER)
        path.chmod(0o550 if path.is_dir() else 0o440)
    trusted_input_directory()


def run_as(uid, argv, cwd, seconds):
    if uid not in WORKER_ROLES or os.geteuid() != 0:
        raise RuntimeError("Generated execution requires a dedicated sandbox worker role")

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
    trusted = trusted_input_directory() if uid == GRADER else None
    if trusted is not None:
        env["BIOTASKS_TRUSTED_INPUT_DIR"] = str(trusted)

    def interrupted(_signal, _frame):
        raise TimeoutError("Outer controller interrupted generated execution")

    # Regular files cannot be held open as pipes by a detached descendant.
    # Cleanup still proves the dedicated role stopped before returning output.
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            preexec_fn=drop,
            start_new_session=True,
            stdout=stdout_file,
            stderr=stderr_file,
        )
        previous_handler = signal.signal(signal.SIGTERM, interrupted)
        timed_out = False
        try:
            try:
                process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            try:
                # Kill the original group, plus role descendants that changed it.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stop_role_processes(uid)
                process.wait(timeout=2)
            finally:
                signal.signal(signal.SIGTERM, previous_handler)
        if trusted is not None:
            trusted_input_directory()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stderr = stderr_file.read().decode("utf-8", errors="replace")
        return {
            "exit_code": None if timed_out else process.returncode,
            "timed_out": timed_out,
            "stdout": stdout_file.read().decode("utf-8", errors="replace"),
            "stderr": stderr + ("\nGenerated process exceeded its timeout" if timed_out else ""),
            "role_process_cleanup_verified": True,
            "process_policy": "Foreground execution only; all processes belonging to this dedicated sandbox worker role are stopped before the call returns.",
        }


def prepare(kind, omitted=None):
    shutil.rmtree(CASE, ignore_errors=True)
    CASE.mkdir(mode=0o755)
    shutil.copytree(PRIVATE / "oracle", CASE / "reference")
    (CASE / "reference").chmod(0o755)
    if kind == "empty":
        (CASE / "submission").mkdir()
    elif kind == "misplaced":
        # The submission argument already names the output root. Valid values
        # beneath an extra outputs/ layer must not satisfy the declared paths.
        (CASE / "submission").mkdir()
        shutil.copytree(PRIVATE / "oracle", CASE / "submission/outputs")
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
    if mode == "seal-inputs":
        if os.geteuid() != 0:
            raise RuntimeError("Only the disposable sandbox controller may seal inputs")
        seal_inputs(Path("/work/task-inputs"))
        print(json.dumps({"status": "trusted_inputs_sealed"}))
        return
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
        record["probe_valid_execution"] = record["probe"]["exit_code"] == 0 and before != after
        if hashes(CASE / "reference") != expected or hashes(PRIVATE / "oracle") != expected:
            raise ValueError("Probe changed read-only reference artifacts")
        if not record["probe_valid_execution"] or mode == "probe-check":
            # Submission preflight reveals execution/mutation validity only.
            # The independent probe author must not see grader behavior.
            if record["probe_valid_execution"]:
                record["status"] = "probe_executed"
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
