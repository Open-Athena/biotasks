"""Original-input parity and tamper detection without biological computations."""

import hashlib
import json
import shutil
import subprocess
import sys
from types import SimpleNamespace

import grading_remote as remote
import pytest
from grading_protocol import artifact_interface
from scientific_bundle import VERIFY


def staged_inputs(tmp_path, monkeypatch):
    private, trusted, source = [tmp_path / p for p in ("private", "trusted", "source")]
    private.mkdir()
    source.mkdir()
    (source / "entities.txt").write_text("alpha\nbeta\n")
    (private / "expected-inputs.json").write_text(json.dumps(remote.hashes(source)))
    monkeypatch.setattr(remote, "PRIVATE", private)
    monkeypatch.setattr(remote, "TRUSTED_INPUTS", trusted)
    ownership = []
    monkeypatch.setattr(remote.os, "chown", lambda *args: ownership.append(args))
    remote.seal_inputs(source)
    return private, trusted, source, ownership


def test_sealed_inputs_keep_original_identity_and_grader_only_permissions(tmp_path, monkeypatch):
    _, trusted, source, ownership = staged_inputs(tmp_path, monkeypatch)
    assert remote.trusted_input_directory() == trusted
    assert ownership == [(trusted, 0, remote.GRADER), (trusted / "entities.txt", 0, remote.GRADER)]
    assert trusted.stat().st_mode & 0o777 == 0o550
    assert (trusted / "entities.txt").stat().st_mode & 0o777 == 0o440
    # Editing the author/solver-facing copy cannot change the private authority.
    (source / "entities.txt").write_text("invented\n")
    assert remote.trusted_input_directory() == trusted
    (trusted / "entities.txt").chmod(0o600)
    (trusted / "entities.txt").write_text("invented\n")
    with pytest.raises(ValueError, match="original identities"):
        remote.trusted_input_directory()


@pytest.mark.parametrize("uid", [remote.AUTHOR, remote.PROBE, remote.ORACLE, remote.GRADER])
def test_only_grader_process_receives_portable_input_path(tmp_path, monkeypatch, uid):
    _, trusted, _, _ = staged_inputs(tmp_path, monkeypatch)
    captured = {}

    def spawn(*_args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pid=99999999, returncode=0, wait=lambda **_kwargs: None)

    monkeypatch.setattr(remote.os, "geteuid", lambda: 0)
    monkeypatch.setattr(remote.os, "killpg", lambda *_args: None)
    monkeypatch.setattr(remote, "stop_role_processes", lambda _uid: None)
    monkeypatch.setattr(remote.subprocess, "Popen", spawn)
    result = remote.run_as(uid, ["not-executed"], tmp_path, 1)
    assert result["exit_code"] == 0
    assert captured["env"].get("BIOTASKS_TRUSTED_INPUT_DIR") == (
        str(trusted) if uid == remote.GRADER else None
    )


def test_original_manifest_refuses_missing_or_symlinked_directory(tmp_path, monkeypatch):
    _, trusted, source, _ = staged_inputs(tmp_path, monkeypatch)
    (trusted / "entities.txt").chmod(0o600)
    trusted.chmod(0o700)
    shutil.rmtree(trusted)
    with pytest.raises(ValueError, match="missing or unsafe"):
        remote.trusted_input_directory()
    trusted.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="missing or unsafe"):
        remote.trusted_input_directory()


def test_control_detects_grader_mutation_after_child_returns(tmp_path, monkeypatch):
    _, trusted, _, _ = staged_inputs(tmp_path, monkeypatch)

    def wait(**_kwargs):
        path = trusted / "entities.txt"
        path.chmod(0o600)
        path.write_text("changed by grader")

    monkeypatch.setattr(remote.os, "geteuid", lambda: 0)
    monkeypatch.setattr(remote.os, "killpg", lambda *_args: None)
    monkeypatch.setattr(remote, "stop_role_processes", lambda _uid: None)
    monkeypatch.setattr(
        remote.subprocess,
        "Popen",
        lambda *_args, **_kwargs: SimpleNamespace(pid=99999999, returncode=0, wait=wait),
    )
    with pytest.raises(ValueError, match="original identities"):
        remote.run_as(remote.GRADER, ["not-executed"], tmp_path, 1)


def test_legacy_grader_without_task_input_capability_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(remote, "PRIVATE", tmp_path)
    assert remote.trusted_input_directory() is None
    assert "trusted_inputs" not in artifact_interface(["result.txt"])
    interface = artifact_interface(["result.txt"], input_paths=["entities.txt"])
    assert interface["trusted_inputs"]["environment_variable"] == "BIOTASKS_TRUSTED_INPUT_DIR"
    assert interface["trusted_inputs"]["input_paths"] == ["entities.txt"]


def native_fixture(tmp_path, *, value, tamper=False):
    tests, outputs, workspace_inputs, logs = [
        tmp_path / p for p in ("tests", "outputs", "workspace-inputs", "logs")
    ]
    for directory in [tests / "inputs", outputs, workspace_inputs, logs]:
        directory.mkdir(parents=True)
    (tests / "inputs/entities.txt").write_text("alpha\nbeta\n")
    (workspace_inputs / "entities.txt").write_text("invented\n")
    (outputs / "result.txt").write_text(value)
    (tests / "checks.json").write_text(json.dumps([{"id": "member", "kind": "scientific"}]))
    (tests / "outputs.json").write_text(json.dumps(["result.txt"]))
    (tests / "inputs-manifest.json").write_text(json.dumps(remote.hashes(tests / "inputs")))
    # A synthetic grader demonstrates an alternative absent from the reference
    # and rejection of an invented entity added to the mutable workspace copy.
    (tests / "grade.py").write_text(
        "import argparse,json,os\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser()\n"
        "for k in ('reference-dir','submission-dir','report'):p.add_argument('--'+k)\n"
        "a=p.parse_args()\n"
        "i=Path(os.environ['BIOTASKS_TRUSTED_INPUT_DIR'])/'entities.txt'\n"
        "passed=(Path(a.submission_dir)/'result.txt').read_text() in i.read_text().splitlines()\n"
        + ("i.write_text('changed by grader')\n" if tamper else "")
        + "Path(a.report).write_text(json.dumps({'passed':passed,'checks':[{'id':'member','passed':passed}]}))\n"
    )
    code = (
        VERIFY.replace("/workspace/outputs", str(outputs))
        .replace("/logs/verifier", str(logs))
        .replace("/tests", str(tests))
        .replace("['python',", "[" + repr(sys.executable) + ",")
    )
    return code, tests, logs


@pytest.mark.parametrize("value,expected", [("alpha", "1"), ("beta", "1"), ("invented", "0")])
def test_native_verifier_uses_original_inputs_for_valid_alternatives_and_wrong_entities(
    tmp_path, value, expected
):
    code, _, logs = native_fixture(tmp_path, value=value)
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert (logs / "reward.txt").read_text().strip() == expected


@pytest.mark.parametrize("when", ["before", "during"])
def test_native_input_mutation_fails_closed_without_stale_reward(tmp_path, when):
    code, tests, logs = native_fixture(tmp_path, value="alpha", tamper=when == "during")
    (logs / "reward.txt").write_text("1\n")
    if when == "before":
        (tests / "inputs/entities.txt").write_text("invented\n")
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert completed.returncode != 0
    assert "input identities changed" in completed.stderr
    assert not (logs / "reward.txt").exists()


def test_native_input_manifest_keeps_original_bytes(tmp_path):
    _, tests, _ = native_fixture(tmp_path, value="alpha")
    assert json.loads((tests / "inputs-manifest.json").read_text()) == {
        "entities.txt": hashlib.sha256(b"alpha\nbeta\n").hexdigest()
    }
