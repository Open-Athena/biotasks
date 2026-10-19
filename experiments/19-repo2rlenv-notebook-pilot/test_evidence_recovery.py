"""Parallel diagnostic retrieval preserves original hashes and output ordering."""

import base64
import hashlib
import json

import pytest
from recover_evidence import main, priority


def prepare(tmp_path, monkeypatch):
    records = []
    for name, data in [
        ("grading/result.json", b'{"status":"fixture"}'),
        ("native/terminus-2/job/trial/agent/trajectory.json", b'{"messages":[]}' + b" " * 300_000),
        ("grading/trace.txt", b"trace" * 2000),
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records.append(
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    (tmp_path / "export-manifest.json").write_text(json.dumps({"files": records}))
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", tmp_path.as_uri())
    return records


def test_recovery_preserves_bytes_and_order(tmp_path, monkeypatch, capsys):
    records = prepare(tmp_path, monkeypatch)
    main()
    lines = capsys.readouterr().out.splitlines()
    chunks = {}
    for line in lines:
        if line.startswith("RECOVERY_CHUNK "):
            chunk = json.loads(line.removeprefix("RECOVERY_CHUNK "))
            encoded = chunks.setdefault(chunk["path"], "")
            assert chunk["offset"] == len(encoded)
            chunks[chunk["path"]] += chunk["data"]
    assert list(chunks) == [record["path"] for record in records]
    for name, encoded in chunks.items():
        assert base64.b64decode(encoded) == (tmp_path / name).read_bytes()
    assert lines[-1].startswith("RECOVERY_COMPLETE ")


def test_recovery_rejects_changed_evidence(tmp_path, monkeypatch, capsys):
    prepare(tmp_path, monkeypatch)
    (tmp_path / "grading/result.json").write_text("changed")
    with pytest.raises(ValueError, match="original export hash"):
        main()
    assert "RECOVERY_COMPLETE " not in capsys.readouterr().out


def test_reference_lock_is_recovered_before_tool_traces(tmp_path, monkeypatch, capsys):
    records = prepare(tmp_path, monkeypatch)
    name = "reference-setup/setup/trials/1/uv.lock"
    data = b"# resolved dependencies\n" + b" " * 400_000
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    lock = {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    records.append(lock)
    (tmp_path / "export-manifest.json").write_text(json.dumps({"files": records}))
    assert priority(lock) < priority({"path": "reference-setup/worker/trace.jsonl"})
    main()
    parts = []
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("RECOVERY_CHUNK "):
            chunk = json.loads(line.removeprefix("RECOVERY_CHUNK "))
            if chunk["path"] == name:
                parts.append(chunk["data"])
    assert base64.b64decode("".join(parts)) == data
