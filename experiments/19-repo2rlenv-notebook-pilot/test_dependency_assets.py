"""Exact installed-file removal using synthetic packages; never touch this VM's packages."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from dependency_assets import apply_manifest, validate_manifest
from reference_replay import load_dependency_exclusions


def fixture(tmp_path):
    root = tmp_path / "site-packages"
    asset = root / "example/tests/expected.txt"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"unused expected answer")
    retained = asset.with_name("input.txt")
    retained.write_bytes(b"required real input")
    item = dict(
        distribution="example",
        path="example/tests/expected.txt",
        sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
        reason="Matched reference output; reference never reads this fixture.",
    )
    package = SimpleNamespace(files=[Path(item["path"])], locate_file=lambda name: root / name)
    return root, asset, retained, item, lambda name: package


def test_removal_checks_installed_identity_and_preserves_inputs(tmp_path):
    root, asset, retained, item, distribution = fixture(tmp_path)
    result = apply_manifest({"files": [item]}, distribution=distribution, roots=[root])
    assert not asset.exists() and retained.read_bytes() == b"required real input"
    assert result == {
        "files": [{key: item[key] for key in ("distribution", "path", "sha256")}],
        "excluded_files_absent": True,
    }
    # A stale manifest cannot claim a fresh removal succeeded.
    with pytest.raises(ValueError, match="regular files"):
        apply_manifest({"files": [item]}, distribution=distribution, roots=[root])


@pytest.mark.parametrize("failure", ["hash", "unowned", "outside", "symlink", "metadata", "notice"])
def test_bad_manifest_removes_nothing(tmp_path, failure):
    root, asset, retained, item, distribution = fixture(tmp_path)
    broken = dict(item)
    if failure == "hash":
        broken["sha256"] = "0" * 64
    elif failure == "unowned":
        broken["path"] = "example/tests/input.txt"
    elif failure == "outside":
        root = tmp_path / "other-environment"
    elif failure == "symlink":
        linked = asset.with_name("linked.txt")
        asset.rename(linked)
        asset.symlink_to(linked)
    elif failure == "metadata":
        broken["path"] = "example-1.dist-info/RECORD"
    else:
        broken["path"] = "example/LICENSE.txt"
    with pytest.raises(ValueError):
        apply_manifest({"files": [broken]}, distribution=distribution, roots=[root])
    assert asset.exists() and retained.read_bytes() == b"required real input"


def test_whole_manifest_verified_before_any_deletion(tmp_path):
    root, asset, _, item, distribution = fixture(tmp_path)
    other = dict(item, path="not-installed.txt")
    with pytest.raises(ValueError):
        apply_manifest({"files": [item, other]}, distribution=distribution, roots=[root])
    assert asset.exists()
    with pytest.raises(ValueError, match="Duplicate"):
        validate_manifest({"files": [item, dict(item, distribution="EXAMPLE")]})


@pytest.mark.parametrize("path", ["../answer", "/answer", "a/../answer", "a//answer", ".", ""])
def test_paths_are_normalized_and_environment_relative(tmp_path, path):
    _, _, _, item, _ = fixture(tmp_path)
    with pytest.raises(ValueError):
        validate_manifest({"files": [dict(item, path=path)]})


def test_frozen_removal_evidence_requires_matching_manifest_and_receipt(tmp_path):
    import json

    _, _, _, item, _ = fixture(tmp_path)
    manifest = {"files": [item]}
    receipt = {
        "files": [{key: item[key] for key in ("distribution", "path", "sha256")}],
        "excluded_files_absent": True,
    }
    records = {}
    for name, data in {
        "candidate/dependency-exclusions.json": json.dumps(manifest),
        "trial/dependency_assets.py": "frozen trusted helper",
        "trial/dependency-exclusions-applied.json": json.dumps(receipt),
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert load_dependency_exclusions(tmp_path, records) == manifest
    receipt["files"] = []
    path = tmp_path / "trial/dependency-exclusions-applied.json"
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="identity mismatch"):
        load_dependency_exclusions(tmp_path, records)
    records[path.relative_to(tmp_path).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="do not match"):
        load_dependency_exclusions(tmp_path, records)
    with pytest.raises(ValueError, match="Unrecorded"):
        load_dependency_exclusions(tmp_path, {})
