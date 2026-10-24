"""Exact installed-file removal using synthetic packages; never touch this VM's packages."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from dependency_assets import (
    apply_manifest,
    imported_module_terms,
    inspect_assets,
    validate_manifest,
)
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


def test_installed_catalog_exposes_answer_candidates_without_selecting_or_deleting(tmp_path):
    root, asset, retained, item, _ = fixture(tmp_path)
    entries = [
        item["path"],
        "example/tests/input.txt",
        "example/core.py",
        "example/tests/test_core.py",
        "example/NOTICE.txt",
    ]
    for name in entries[2:]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ordinary package file")
    linked = root / "example/tests/linked.txt"
    linked.symlink_to(asset)
    package = SimpleNamespace(
        metadata={"Name": "example"},
        files=[*entries, "example/tests/linked.txt"],
        locate_file=lambda name: root / name,
    )
    catalog = inspect_assets(
        [{"path": "expected.txt", "sha256": item["sha256"]}],
        distributions=lambda: [package],
        roots=[root],
    )
    records = {row["path"]: row for row in catalog["files"]}
    assert item["path"] in records and "example/core.py" not in records
    assert "example/tests/test_core.py" in records and "example/tests/linked.txt" not in records
    assert not records["example/NOTICE.txt"]["eligible_for_declared_removal"]
    assert catalog["summary"]["priority_matches"] == [records[item["path"]]]
    assert any("identical_bytes" in row["reasons"] for row in records[item["path"]]["matches"])
    assert asset.exists() and retained.read_bytes() == b"required real input"
    # Different serialized bytes still surface by name; no false safety claim.
    changed = inspect_assets(
        [{"path": "expected.txt", "sha256": "0" * 64}],
        distributions=lambda: [package],
        roots=[root],
    )
    assert changed["summary"]["priority_matches"][0]["path"] == item["path"]


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


@pytest.mark.parametrize("name", ["ToolkitTests", "toolkit-tests", "toolkit_testsuite"])
def test_dedicated_test_distribution_data_is_visible_without_matching_output_name(tmp_path, name):
    root = tmp_path / "site-packages"
    relative = name.replace("-", "_") + "/data/known_values.bin"
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"scientific fixture; not presumed an unused answer")
    package = SimpleNamespace(
        metadata={"Name": name}, files=[relative], locate_file=lambda p: root / p
    )
    result = inspect_assets(
        [{"path": "table.csv", "sha256": "0" * 64, "bytes": 100}],
        distributions=lambda: [package],
        roots=[root],
    )
    assert [item["path"] for item in result["files"]] == [relative]
    assert result["files"][0]["packaged_test_or_example"]
    assert result["files"][0]["matches"] == []
    assert result["summary"]["distribution_coverage"] == [
        {
            "distribution": name,
            "installed_regular_files_inspected": 1,
            "candidate_files": 1,
            "dedicated_test_distribution_hint": True,
        }
    ]
    assert path.exists()  # Discovery never selects or removes a fixture.


def test_renamed_exact_answer_is_detected_without_a_filename_or_test_directory_hint(tmp_path):
    root = tmp_path / "site-packages"
    for name, data in [
        ("library/cache/opaque.dat", b"complete answer"),
        ("library/cache/other.dat", b"unrelated bytes"),
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    assert len(b"complete answer") == len(b"unrelated bytes")
    package = SimpleNamespace(
        metadata={"Name": "library"},
        files=["library/cache/opaque.dat", "library/cache/other.dat"],
        locate_file=lambda p: root / p,
    )
    result = inspect_assets(
        [
            {
                "path": "result.csv",
                "sha256": hashlib.sha256(b"complete answer").hexdigest(),
                "bytes": len(b"complete answer"),
            }
        ],
        distributions=lambda: [package],
        roots=[root],
    )
    assert [row["path"] for row in result["files"]] == ["library/cache/opaque.dat"]
    assert result["summary"]["priority_matches"] == result["files"]
    assert result["files"][0]["matches"] == [
        {"output": "result.csv", "reasons": ["identical_bytes"]}
    ]
    assert not result["files"][0]["packaged_test_or_example"]
    assert result["summary"]["distribution_coverage"][0]["installed_regular_files_inspected"] == 2
    assert all((root / name).exists() for name in package.files)


@pytest.mark.parametrize("module", ["trends", "sample_stats"])
def test_imported_analysis_module_prioritizes_test_source_without_output_name_match(
    tmp_path, module
):
    root = tmp_path / "site-packages"
    entries = [f"toolkit/tests/test_{module}.py", f"toolkit/tests/test_de{module}.py"]
    for name in entries:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("expected_measurement = 1.234567\n")
    package = SimpleNamespace(
        metadata={"Name": "toolkit"}, files=entries, locate_file=lambda name: root / name
    )
    source = f"from toolkit.analysis import {module} as t\nraise RuntimeError('never execute')\n"
    result = inspect_assets(
        [{"path": "measurements.csv", "sha256": "0" * 64}],
        distributions=lambda: [package],
        roots=[root],
        source=source,
    )
    priority = result["summary"]["priority_matches"]
    assert len(priority) == 1 and priority[0]["path"] == entries[0]
    assert priority[0]["source_import_matches"] == [module]
    assert priority[0]["matches"] == []  # No claim of an output-content match.
    assert result["summary"]["source_import_terms"] == ["analysis", module]
    assert len(result["files"]) == 2  # Nonpriority candidates remain inspectable.
    assert all((root / name).read_text() == "expected_measurement = 1.234567\n" for name in entries)


def test_import_hints_preserve_literal_names_without_alias_or_execution_claims():
    source = """import toolkit.metrics as m
from toolkit.other import *
if False:
    from toolkit.helpers import dormant as alias
"""
    assert imported_module_terms(source) == ["dormant", "helpers", "metrics", "other"]
    with pytest.raises(SyntaxError):
        imported_module_terms("from broken import")


def test_inspection_command_reads_the_supplied_source_without_executing_it(
    tmp_path, monkeypatch, capsys
):
    import importlib.metadata
    import json
    import runpy
    import sys
    import sysconfig

    root = tmp_path / "site-packages"
    name = "toolkit/tests/test_trends.py"
    asset = root / name
    asset.parent.mkdir(parents=True)
    asset.write_text("known_value = 12.345\n")
    package = SimpleNamespace(
        metadata={"Name": "toolkit"}, files=[name], locate_file=lambda path: root / path
    )
    source = tmp_path / "source.py"
    source.write_text("from toolkit.analysis import trends\nraise RuntimeError('not executed')\n")
    inventory = tmp_path / "outputs.json"
    inventory.write_text(json.dumps([{"path": "results.csv", "sha256": "0" * 64}]))
    destination = tmp_path / "catalog.json"
    script = Path(__file__).with_name("dependency_assets.py")
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: [package])
    monkeypatch.setattr(sysconfig, "get_path", lambda key: str(root))
    monkeypatch.setattr(sys, "prefix", "fixture-task-venv")
    monkeypatch.setattr(
        sys, "argv", [str(script), "inspect", str(inventory), str(destination), str(source)]
    )
    runpy.run_path(str(script), run_name="__main__")
    saved = json.loads(destination.read_text())
    reported = json.loads(capsys.readouterr().out)
    assert reported == saved["summary"]
    assert reported["priority_matches"][0]["path"] == name
    assert reported["priority_matches"][0]["source_import_matches"] == ["trends"]
    assert asset.read_text() == "known_value = 12.345\n"
