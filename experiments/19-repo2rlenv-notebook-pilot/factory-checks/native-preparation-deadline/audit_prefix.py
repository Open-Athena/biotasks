"""Recognize a definite pre-Harbor failure; never infer cleanup from a timeout."""

import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

HARBOR_SOURCES = {
    "517c8748fa5c1fc6b456907d0d0fe5283cbcdb1756a6d7fba0f0d485a34f8eac",
    "bb1bdd1aa3246ba773575eb596b40b5b7eb7baca6f7e7a851c20015d6313e05b",
}
IRIS_SOURCE = "086c481d0925af19c7eef6d0a0a67df8a5dd8c1c1d7888551bf4c53504613ac9"
E = "experiments/19-repo2rlenv-notebook-pilot/"
SDK_FOLDERS = ("setup-raw", "replay", "materialization-raw", "grading")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen_sources(payload, submitted_hashes):
    """Rebuild the small runner file from the original archive and pinned patches."""
    for name in ("biotasks.tar", "upstream.tar.gz"):
        with (payload / name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == submitted_hashes[name]
    with tarfile.open(payload / "biotasks.tar") as archive:
        pin = json.loads(archive.extractfile(E + "upstream-pin.json").read())
        iris = archive.extractfile(E + "iris_execution.py").read()
        patches = []
        for row in pin["patches"]:
            raw = archive.extractfile(E + row["path"]).read()
            assert digest(raw) == row["sha256"]
            patches.append(raw.decode())
    name = "src/repo2rlenv/execution/harbor.py"
    with tarfile.open(payload / "upstream.tar.gz") as archive:
        members = [m for m in archive if m.name.endswith("/" + name)]
        assert len(members) == 1
        source = archive.extractfile(members[0]).read()
    assert digest(source) == next(row["sha256"] for row in pin["files"] if row["path"] == name)
    with tempfile.TemporaryDirectory(prefix="biotasks19-native-prefix-source-") as temporary:
        root = Path(temporary)
        target = root / name
        target.parent.mkdir(parents=True)
        target.write_bytes(source)
        for patch in patches:
            sections = re.split(r"(?=^--- a/)", patch, flags=re.MULTILINE)
            selected = [s for s in sections if s.startswith(f"--- a/{name}\n+++ b/{name}\n")]
            if selected:
                subprocess.run(
                    ["patch", "-p1", "--batch", "--fuzz=0"],
                    cwd=root,
                    input="".join(selected).encode(),
                    check=True,
                    capture_output=True,
                )
        source_hash = digest(target.read_bytes())
    assert source_hash in HARBOR_SOURCES and digest(iris) == IRIS_SOURCE
    return {
        "patched_harbor_sha256": source_hash,
        "iris_execution_sha256": digest(iris),
        "original_upstream_sha256": submitted_hashes["upstream.tar.gz"],
    }


def audit_no_dispatch(pipeline, native, trial, claims, paths, sources):
    """Known source preserves command/dispatch fields before any job launch."""
    assert sources["patched_harbor_sha256"] in HARBOR_SOURCES
    assert sources["iris_execution_sha256"] == IRIS_SOURCE
    assert pipeline["status"] == "infrastructure_failed" and pipeline["failed_stage"] == "native"
    assert [row["name"] for row in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
        "native",
    ]
    assert all(row["status"] == "completed" for row in pipeline["stages"][:-1])
    assert pipeline["stages"][-1]["status"] == "incomplete" and "finished" in pipeline
    assert native == {
        "status": "incomplete",
        "controls": [],
        "solver": None,
        "publication_ready": False,
        "finished": native["finished"],
    }
    assert trial["agent"] == "oracle" and trial["model"] is None
    assert trial["state"] == "interrupted" and not trial.get("trial_dispatched", False)
    assert "command" not in trial  # The known source never removes a dispatched command.
    assert len(claims) == 1 and claims[0]["trial_id"] == trial["trial_id"]
    assert claims[0]["solving"] is False and not claims[0].get("cleanup_verified", False)
    assert sorted(p for p in paths if p.endswith("/sandbox-claim.json")) == sorted(
        folder + "/sandbox-claim.json" for folder in SDK_FOLDERS
    )
    assert [p for p in paths if p.startswith("native/") and p.endswith("/trial.json")] == [
        "native/oracle/trial.json"
    ]
    assert not any(p.startswith("native/") and p.endswith("/remote-job.json") for p in paths)
    assert not any(p.startswith(("native/nop/", "native/terminus-2/")) for p in paths)
    return {
        "native_supervisor_dispatched": False,
        "native_resources_created": False,
        "native_cleanup_applicable": False,
        "sources": sources,
        "reason": "Exact known runner writes and retains command/dispatch fields before launch. The original interrupted oracle has neither, no controls/solver or supervisor receipt, and one uncompleted non-solving claim. Fresh SDK cleanup must still be verified separately.",
    }
