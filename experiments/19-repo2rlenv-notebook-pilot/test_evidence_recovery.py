"""Parallel diagnostic retrieval preserves original hashes and output ordering."""

import base64
import hashlib
import json

import pytest
from recover_evidence import main


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
