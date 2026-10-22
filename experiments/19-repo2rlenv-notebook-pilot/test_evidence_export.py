"""Streaming export preserves exact bytes and refuses credentials/symlinks."""

import hashlib
import json
import sys
import time

import pytest
from iris_bootstrap import export


def test_export_download_checks_every_file(tmp_path, monkeypatch):
    for name in ("GLM_BULK_TOKEN", "DAYTONA_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (source / "large").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    (source / "small").write_text("data")
    export(source, target.as_uri())
    result = json.loads((target / "export-manifest.json").read_text())
    assert result["download_checked"]
    assert [r["path"] for r in result["files"]] == ["large", "small"]
    for record in result["files"]:
        data = (target / record["path"]).read_bytes()
        assert len(data) == record["bytes"] and hashlib.sha256(data).hexdigest() == record["sha256"]


def test_export_refuses_secret_spanning_chunks(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "fixture-secret-only")
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (source / "bad").write_bytes(b"x" * (1024 * 1024 - 5) + b"fixture-secret-only")
    with pytest.raises(ValueError, match="Credential detected"):
        export(source, target.as_uri())
    assert not (target / "export-manifest.json").exists()


def test_export_refuses_symlinks(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "link").symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="symlinks"):
        export(source, (tmp_path / "target").as_uri())


def test_active_export_can_outlive_inactivity_allowance(tmp_path):
    from iris_bootstrap import command

    script = (
        "import os,time; fd=int(os.environ['BIOTASKS_EXPORT_PROGRESS_FD']); "
        "[(os.write(fd,b'.'),time.sleep(.2)) for _ in range(7)]"
    )
    command(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        deadline=time.time() + 8,
        log=tmp_path / "active.log",
        progress_timeout=1,
    )


def test_stalled_export_stops_its_owned_process(tmp_path, monkeypatch):
    import iris_bootstrap

    processes = []
    spawn = iris_bootstrap.subprocess.Popen

    def capture(*args, **kwargs):
        process = spawn(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(iris_bootstrap.subprocess, "Popen", capture)
    with pytest.raises(iris_bootstrap.ExportStalled):
        iris_bootstrap.command(
            [sys.executable, "-c", "import time;time.sleep(30)"],
            cwd=tmp_path,
            deadline=time.time() + 8,
            log=tmp_path / "stalled.log",
            progress_timeout=0.5,
        )
    assert len(processes) == 1 and processes[0].poll() is not None


@pytest.mark.parametrize("failure", ["stall", "integrity", "deadline"])
def test_export_retries_only_stall_without_extending_deadline(tmp_path, monkeypatch, failure):
    import iris_bootstrap

    calls = []
    deadline = time.time() + 60
    monkeypatch.setenv("BIOTASKS_EXPORT_PYTHON", sys.executable)

    def invoke(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            if failure == "stall":
                raise iris_bootstrap.ExportStalled("fixture")
            if failure == "integrity":
                raise RuntimeError("integrity guard")
            raise TimeoutError("campaign deadline")

    monkeypatch.setattr(iris_bootstrap, "command", invoke)
    if failure == "stall":
        iris_bootstrap.export_on_host(
            tmp_path / "source", "s3://fixture/recovery", deadline=deadline
        )
        assert len(calls) == 2
    else:
        with pytest.raises((RuntimeError, TimeoutError)):
            iris_bootstrap.export_on_host(
                tmp_path / "source", "s3://fixture/recovery", deadline=deadline
            )
        assert len(calls) == 1
    assert all(call[1]["deadline"] == deadline for call in calls)
    assert all(
        call[0][0][2:] == ["--export", str(tmp_path / "source"), "s3://fixture/recovery"]
        for call in calls
    )


def test_final_diagnostics_survive_storage_failure_without_credential_output(tmp_path, monkeypatch):
    import iris_bootstrap

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "bootstrap-status.json").write_text('{"completed": true}')
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture/final")
    monkeypatch.setenv("HF_TOKEN", "fixture-secret-value")
    calls = []

    def fail(root, prefix, *, deadline, log):
        assert not log.is_relative_to(evidence)
        log.write_text("transport failure fixture-secret-value")
        raise RuntimeError("fixture storage unavailable")

    monkeypatch.setattr(iris_bootstrap, "export_on_host", fail)
    monkeypatch.setattr(iris_bootstrap.runpy, "run_path", lambda *a, **kw: calls.append(a))
    with pytest.raises(RuntimeError, match="storage unavailable"):
        iris_bootstrap.export_final_evidence(
            evidence, tmp_path / "inputs", deadline=time.time() + 60
        )
    assert len(calls) == 1
    assert "fixture-secret-value" not in (evidence / "archive.log").read_text()
    status = json.loads((evidence / "bootstrap-status.json").read_text())
    assert status["archive_error_type"] == "RuntimeError"
    assert status["completed"] is True
