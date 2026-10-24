"""Streaming export preserves exact bytes and refuses credentials/symlinks."""

import hashlib
import io
import json
import sys
import tarfile
import time

import pytest
from iris_bootstrap import CREDENTIAL_ENV_NAMES, export


def test_export_download_checks_every_file(tmp_path, monkeypatch):
    for name in CREDENTIAL_ENV_NAMES:
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


@pytest.mark.parametrize("credential", CREDENTIAL_ENV_NAMES)
def test_export_refuses_secret_spanning_chunks(tmp_path, monkeypatch, credential):
    monkeypatch.setenv(credential, "fixture-secret-only")
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


@pytest.mark.parametrize("credential", CREDENTIAL_ENV_NAMES)
def test_final_diagnostics_survive_storage_failure_without_credential_output(
    tmp_path, monkeypatch, credential
):
    import iris_bootstrap

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "bootstrap-status.json").write_text('{"completed": true}')
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture/final")
    monkeypatch.setenv(credential, "fixture-secret-value")
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


def test_snapshot_roundtrip_preserves_nested_bytes_modes_and_transport_seal(tmp_path, monkeypatch):
    import iris_bootstrap

    for name in CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    source, target = tmp_path / "source", tmp_path / "target"
    (source / "trace/1").mkdir(parents=True)
    target.mkdir()
    (source / "trace/1/response.json").write_bytes(b"original" * 300_000)
    (source / "solve.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
    (source / "solve.sh").chmod(0o755)
    iris_bootstrap.snapshot(source, target.as_uri())
    manifest = json.loads((target / "snapshot-files.json").read_text())
    assert manifest["source_quiescent"]
    with tarfile.open(target / "evidence.tar.gz") as archive:
        assert set(archive.getnames()) == {"files/" + row["path"] for row in manifest["files"]}
        for row in manifest["files"]:
            member = archive.getmember("files/" + row["path"])
            data = archive.extractfile(member).read()
            assert data == (source / row["path"]).read_bytes()
            assert len(data) == row["bytes"]
            assert hashlib.sha256(data).hexdigest() == row["sha256"]
            assert member.mode == row["mode"] == (source / row["path"]).stat().st_mode & 0o777
    transport = json.loads((target / "export-manifest.json").read_text())
    assert transport["download_checked"]
    for row in transport["files"]:
        assert hashlib.sha256((target / row["path"]).read_bytes()).hexdigest() == row["sha256"]


@pytest.mark.parametrize("defect", ["credential", "symlink", "mutation"])
def test_snapshot_failure_never_publishes_a_seal(tmp_path, monkeypatch, defect):
    import iris_bootstrap

    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    path = source / "trace.json"
    path.write_bytes(b"x" * (16 * 1024 - 5) + b"fixture-secret-only")
    if defect == "credential":
        monkeypatch.setenv("GLM_BULK_TOKEN", "fixture-secret-only")
    elif defect == "symlink":
        (source / "link").symlink_to(path)
    else:
        original = tarfile.TarFile.addfile

        def mutate(self, tarinfo, fileobj=None):
            original(self, tarinfo, fileobj)
            path.write_bytes(b"changed source")

        monkeypatch.setattr(tarfile.TarFile, "addfile", mutate)
    with pytest.raises(ValueError):
        iris_bootstrap.snapshot(source, target.as_uri())
    assert not list(target.iterdir())


@pytest.mark.parametrize("fails", [False, True])
def test_failure_snapshot_uses_only_cleanup_time_and_preserves_primary_status(
    tmp_path, monkeypatch, fails
):
    import iris_bootstrap

    source = tmp_path / "work/campaign"
    source.mkdir(parents=True)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    status_path = evidence / "bootstrap-status.json"
    status_path.write_text('{"completed": false, "error_type": "TimeoutExpired"}')
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture/campaign")
    monkeypatch.setattr(iris_bootstrap.time, "time", lambda: 100)
    calls = []

    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        if fails:
            raise RuntimeError("snapshot upload failed")

    monkeypatch.setattr(iris_bootstrap, "command", invoke)
    iris_bootstrap.export_failure_snapshot(
        tmp_path,
        {"entrypoint": "run_autonomous.py", "campaign": "campaign"},
        evidence,
        deadline=400,
        source_root=source.parent,
    )
    assert len(calls) == 1
    assert calls[0][0][2:] == [
        "--snapshot",
        str(source),
        "s3://fixture/campaign/autonomous-snapshot",
    ]
    assert calls[0][1]["deadline"] == 340
    status = json.loads(status_path.read_text())
    assert not status["completed"] and status["error_type"] == "TimeoutExpired"
    assert status.get("failure_snapshot_download_checked", False) is not fails
    assert status.get("failure_snapshot_error_type") == ("RuntimeError" if fails else None)


def test_expired_cleanup_does_not_start_snapshot_process(tmp_path, monkeypatch):
    import iris_bootstrap

    source = tmp_path / "work/campaign"
    source.mkdir(parents=True)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "bootstrap-status.json").write_text('{"completed": false}')
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture/campaign")
    monkeypatch.setattr(iris_bootstrap.time, "time", lambda: 100)
    monkeypatch.setattr(
        iris_bootstrap.subprocess, "Popen", lambda *a, **kw: pytest.fail("Expired launch")
    )
    iris_bootstrap.export_failure_snapshot(
        tmp_path,
        {"entrypoint": "run_autonomous.py", "campaign": "campaign"},
        evidence,
        deadline=99,
        source_root=source.parent,
    )
    status = json.loads((evidence / "bootstrap-status.json").read_text())
    assert status["failure_snapshot_error_type"] == "TimeoutError"
    assert "failure_snapshot_download_checked" not in status


def test_snapshot_restore_preserves_exact_originals_and_never_overwrites(tmp_path, monkeypatch):
    import iris_bootstrap

    for name in CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    source, transport, restored = (tmp_path / name for name in ("source", "transport", "restored"))
    source.mkdir()
    transport.mkdir()
    (source / "pipeline.json").write_text('{"status":"infrastructure_failed"}')
    (source / "executable.py").write_bytes(b"original bytes\n")
    (source / "executable.py").chmod(0o755)
    iris_bootstrap.snapshot(source, transport.as_uri())
    before = {p.name: p.read_bytes() for p in transport.iterdir()}
    receipt = iris_bootstrap.restore_snapshot(transport, restored)
    assert receipt["all_snapshot_files_hash_size_mode_verified"] and receipt["file_count"] == 2
    assert restored.stat().st_mode & 0o777 == 0o700
    for p in source.iterdir():
        copy = restored / "files" / p.name
        assert copy.read_bytes() == p.read_bytes()
        assert copy.stat().st_mode & 0o777 == p.stat().st_mode & 0o777
    assert (
        json.loads((restored / "files/pipeline.json").read_text())["status"]
        == "infrastructure_failed"
    )
    assert (restored / "snapshot-files.json").read_bytes() == before["snapshot-files.json"]
    assert {p.name: p.read_bytes() for p in transport.iterdir()} == before
    with pytest.raises(FileExistsError):
        iris_bootstrap.restore_snapshot(transport, restored)
    result = iris_bootstrap.subprocess.run(
        [
            sys.executable,
            str(iris_bootstrap.__file__),
            "--restore-snapshot",
            str(transport),
            str(tmp_path / "cli-restored"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == receipt


@pytest.mark.parametrize(
    "defect", ["transport", "traversal", "symlink", "duplicate", "missing", "member_hash"]
)
def test_snapshot_restore_rejects_inconsistent_members_without_final_receipt(
    tmp_path, monkeypatch, defect
):
    import iris_bootstrap

    for name in CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    source, transport, restored = (tmp_path / name for name in ("source", "transport", "restored"))
    source.mkdir()
    transport.mkdir()
    (source / "result.json").write_bytes(b"original")
    iris_bootstrap.snapshot(source, transport.as_uri())
    manifest_path = transport / "snapshot-files.json"
    manifest = json.loads(manifest_path.read_text())
    row = manifest["files"][0]
    if defect == "transport":
        with (transport / "evidence.tar.gz").open("ab") as target:
            target.write(b"tampered")
    else:
        if defect == "traversal":
            row["path"] = "../../escaped"
        manifest_path.write_text(json.dumps(manifest))
        with tarfile.open(transport / "evidence.tar.gz", "w:gz") as archive:
            if defect != "missing":
                member = tarfile.TarInfo("files/" + row["path"])
                member.size, member.mode = row["bytes"], row["mode"]
                data = b"different" if defect == "member_hash" else b"original"
                if defect == "symlink":
                    member.type, member.linkname, member.size = tarfile.SYMTYPE, "../../escaped", 0
                    archive.addfile(member)
                else:
                    archive.addfile(member, io.BytesIO(data))
                    if defect == "duplicate":
                        archive.addfile(member, io.BytesIO(data))
        # Make the transport seal consistent, so per-file checks must detect
        # invalid internal structure rather than only the compressed hash.
        seal_path = transport / "export-manifest.json"
        seal = json.loads(seal_path.read_text())
        for entry in seal["files"]:
            p = transport / entry["path"]
            entry.update(bytes=p.stat().st_size, sha256=iris_bootstrap.digest(p))
        seal_path.write_text(json.dumps(seal))
    before = {p.name: p.read_bytes() for p in transport.iterdir()}
    with pytest.raises(ValueError):
        iris_bootstrap.restore_snapshot(transport, restored)
    assert not (restored / "snapshot-readback.json").exists()
    assert not (tmp_path / "escaped").exists()
    assert {p.name: p.read_bytes() for p in transport.iterdir()} == before


def test_snapshot_restore_refuses_nonregular_metadata_without_opening_it(tmp_path):
    import os

    import iris_bootstrap

    transport = tmp_path / "transport"
    transport.mkdir()
    os.mkfifo(transport / "export-manifest.json")
    with pytest.raises(ValueError, match="regular file"):
        iris_bootstrap.restore_snapshot(transport, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
