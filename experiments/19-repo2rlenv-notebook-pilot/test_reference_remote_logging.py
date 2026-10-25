"""Real small subprocess checks for controller-owned command output."""

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import reference_remote


def test_isolation_exposes_a_real_scratch_copy_and_preserves_authoring_data(tmp_path):
    workspace = tmp_path / "authoring"
    workspace.mkdir()
    scratch = workspace / "download.txt"
    scratch.write_bytes(b"synthetic input\n")
    quarantine = tmp_path / "private"
    observed = reference_remote.isolate_workspace(workspace, quarantine)
    assert observed == {"state": "isolated", "workspace": str(workspace)}
    assert not workspace.exists() and quarantine.stat().st_mode & 0o077 == 0
    output = tmp_path / "staged.txt"
    failed = subprocess.run(
        ["sh", "-eu", "-c", f"cp {shlex.quote(str(scratch))} {shlex.quote(str(output))}"],
        capture_output=True,
    )
    assert failed.returncode != 0 and not output.exists()
    # A self-contained staging operation can still write its declared output.
    subprocess.run(
        ["sh", "-eu", "-c", "printf 'input\\n' > " + shlex.quote(str(output))], check=True
    )
    restored = reference_remote.restore_workspace(workspace, quarantine)
    assert restored["authoring_path_recreated"] is False
    assert scratch.read_bytes() == b"synthetic input\n"
    assert output.read_bytes() == b"input\n"


@pytest.mark.parametrize("replacement", ["directory", "file", "symlink"])
def test_staging_recreation_is_preserved_without_overwriting_original(tmp_path, replacement):
    workspace, quarantine = tmp_path / "authoring", tmp_path / "private"
    workspace.mkdir()
    (workspace / "source.py").write_text("original source\n")
    reference_remote.isolate_workspace(workspace, quarantine)
    target = tmp_path / "unrelated.txt"
    target.write_text("unrelated\n")
    if replacement == "directory":
        workspace.mkdir()
        (workspace / "source.py").write_text("unexpected staging edit\n")
    elif replacement == "file":
        workspace.write_text("unexpected staging file\n")
    else:
        workspace.symlink_to(target)
    restored = reference_remote.restore_workspace(workspace, quarantine)
    preserved = Path(restored["preserved_staging_path"])
    assert restored["authoring_path_recreated"] is True
    assert (workspace / "source.py").read_text() == "original source\n"
    assert target.read_text() == "unrelated\n"
    if replacement == "directory":
        assert (preserved / "source.py").read_text() == "unexpected staging edit\n"
    elif replacement == "file":
        assert preserved.read_text() == "unexpected staging file\n"
    else:
        assert preserved.is_symlink() and preserved.readlink() == target


def test_existing_quarantine_is_never_overwritten(tmp_path):
    workspace, quarantine = tmp_path / "authoring", tmp_path / "private"
    workspace.mkdir()
    quarantine.mkdir()
    (quarantine / "keep.txt").write_text("existing evidence")
    with pytest.raises(FileExistsError):
        reference_remote.isolate_workspace(workspace, quarantine)
    assert workspace.is_dir() and (quarantine / "keep.txt").read_text() == "existing evidence"


@pytest.mark.parametrize("timeout", [False, True])
def test_worker_cleanup_cannot_remove_active_command_log(tmp_path, monkeypatch, capsys, timeout):
    logs = tmp_path / "logs"

    def routed_path(*parts):
        if parts[0] == "/work/logs":
            return logs.joinpath(*parts[1:])
        return Path(*parts)

    monkeypatch.setattr(reference_remote, "Path", routed_path)
    code = (
        "import shutil,sys,time\n"
        "print('before cleanup',flush=True)\n"
        f"shutil.rmtree({str(logs)!r})\n"
        "print('after cleanup',file=sys.stderr,flush=True)\n"
        + ("time.sleep(5)\n" if timeout else "sys.exit(7)\n")
    )
    reference_remote.execute(
        [sys.executable, "-c", code], 0.5 if timeout else 5, str(tmp_path), "trial"
    )
    record = json.loads(capsys.readouterr().out)
    assert record["timed_out"] is timeout
    assert record["exit_code"] != 0 if timeout else record["exit_code"] == 7
    assert (logs / "trial.log").read_text() == "before cleanup\nafter cleanup\n"
    assert json.loads((logs / "trial.json").read_text()) == record
    assert sorted(p.name for p in logs.iterdir()) == ["trial.json", "trial.log"]
