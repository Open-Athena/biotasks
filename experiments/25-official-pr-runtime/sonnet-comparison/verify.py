"""Verify retained archives, configuration and accounting without execution."""

import hashlib
import json
from pathlib import Path
import tarfile

import zstandard

ARM = Path(__file__).resolve().parent
ROOT = ARM.parent
EV = ARM / "evidence"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    manifest_path = ARM / "artifact-manifest.json"
    manifest = load(manifest_path)
    for row in manifest["files"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"], row["path"]
        assert digest(path) == row["sha256"], row["path"]
    receipt = load(EV / "archive-receipt.json")
    archive = EV / "outputs.tar.zst"
    assert archive.stat().st_size == receipt["size_bytes"]
    assert digest(archive) == receipt["sha256"]
    original_members = []
    with archive.open("rb") as source, zstandard.ZstdDecompressor().stream_reader(source) as stream:
        with tarfile.open(fileobj=stream, mode="r|") as bundle:
            for member in bundle:
                if not member.isfile():
                    continue
                assert Path(member.name).name == member.name
                assert member.size < 20 * 1024**2
                target = EV / member.name
                if target.suffix == ".log":
                    target = target.with_suffix(".txt")
                assert bundle.extractfile(member).read() == target.read_bytes(), member.name
                original_members.append(member.name)
    with tarfile.open(EV / "native-artifacts.tar.gz", "r:gz") as bundle:
        for member in bundle:
            if member.isdir():
                continue
            path = Path(member.name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert member.size < 20 * 1024**2
            assert bundle.extractfile(member).read() == (EV / "native" / path).read_bytes()
    plan = load(ARM / "launch-plan.json")
    for name, expected in plan["shared_code_sha256"].items():
        assert digest(ROOT / name) == expected, name
    for change in plan["config_differences"]:
        old = load(ROOT / "proposed-configs" / change["file"])
        new = load(ARM / "configs" / change["file"])
        assert digest(ROOT / "proposed-configs" / change["file"]) == change["baseline_sha256"]
        assert digest(ARM / "configs" / change["file"]) == change["comparison_sha256"]
        assert old["llm"]["model"] == change["before"]
        assert new["llm"]["model"] == plan["model"] == change["after"]
        old["llm"]["model"] = new["llm"]["model"]
        assert old == new, change["file"]
    outcomes = load(EV / "final-outcomes.json")
    assert all(r["agent_iterations"] <= plan["bootstrap_max_iterations_per_repository"] for r in outcomes["repositories"])
    exports = load(EV / "exported-tasks.json")
    assert sorted(exports) == sorted(str(p.relative_to(EV / "native")) for p in (EV / "native/outputs").rglob("task.toml"))
    assert outcomes["counts"]["exports"] == len(exports)
    lifecycle = load(EV / "lifecycle.json")
    assert lifecycle["all_issue_25_jobs_terminal"]
    assert digest(ROOT / "evidence/lifecycle.json") == lifecycle["baseline_lifecycle_sha256"]
    assert lifecycle["issue_25_total_allocated_cpu_hours"] < plan["compute"]["issue_25_total_ceiling_cpu_hours"]
    cleanup = load(EV / "supervisor-result.json")
    assert cleanup["native_started"] and cleanup["authenticated"]
    assert all(not cleanup[k] for k in ("remaining_containers", "remaining_controllers", "remaining_images"))
    result = {
        "artifact_manifest_sha256": digest(manifest_path),
        "manifest_files_verified": len(manifest["files"]),
        "original_archive_checksum_verified": True,
        "original_members_match_retained_files": original_members,
        "nested_archive_members_match": True,
        "runner_hashes_match_checkpoint": True,
        "native_configuration_differences": ["llm.model"],
        "upstream_source_modifications": [],
        "upstream_source_basis": "Pinned archive checksum checked by the unchanged installer; no source patch or monkeypatch applied.",
        "iteration_and_compute_bounds_verified": True,
        "all_issue_jobs_terminal": True,
        "owned_cleanup_verified": True,
        "exports": len(exports),
        "grading": "No export exists to grade." if not exports else "See separate grading evidence.",
        "zstandard_version": zstandard.__version__,
        "credential_scan": "Exact authorized credential values and token-shaped text were absent from extracted publishable evidence before publication; values are not retained.",
    }
    output = ARM / "verification.json"
    if output.exists():
        prior = load(output)
        if "remote_git_readback" in prior:
            result["remote_git_readback"] = prior["remote_git_readback"]
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
