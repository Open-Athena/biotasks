"""Read-only recovery fixtures; no cloud credentials, jobs or biological tasks."""

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("tamper", [False, True])
def test_original_export_hashes_are_required(tmp_path, tamper):
    source = tmp_path / "remote" / "native"
    records = source / "records"
    records.mkdir(parents=True)
    data = b'{"sandboxes": [], "fixture": true}'
    stored = data.replace(b"true", b"null") if tamper else data
    (records / "cleanup.json").write_bytes(stored)
    (source / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "path": "cleanup.json",
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ]
        )
    )
    (tmp_path / "recovery-plan.json").write_text(
        json.dumps(
            [
                {
                    "seed": "fixture",
                    "prefix": (tmp_path / "remote").as_uri(),
                    "native_slots": ["native"],
                }
            ]
        )
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("recover_native_records.py"))],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if tamper:
        assert result.returncode != 0
        assert "Original native export hash mismatch" in result.stderr
        assert "RECOVERY_COMPLETE" not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        line = next(s for s in result.stdout.splitlines() if s.startswith("RECOVERY_MANIFEST "))
        manifest = json.loads(base64.b64decode(line.split(" ", 1)[1]))
        entry = next(e for e in manifest["files"] if e["path"].endswith("records/cleanup.json"))
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()
        assert "RECOVERY_COMPLETE" in result.stdout
    assert (records / "cleanup.json").read_bytes() == stored
