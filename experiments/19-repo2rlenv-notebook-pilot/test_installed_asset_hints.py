"""Installed discovery is private, source-bound evidence, never a removal rule."""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from installed_asset_hints import References, build_hints


def fixture(tmp_path, code=b"expected = -4.9275633\n", tables=None):
    installed = tmp_path / "site-packages"
    target = installed / "example/tests/expected.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(code)
    # If imported or executed, this synthetic scientific package must fail.
    (target.parent.parent / "__init__.py").write_text("raise RuntimeError('DO NOT IMPORT')")
    asset = {
        "distribution": "Example_Tests",
        "path": "example/tests/expected.py",
        "sha256": hashlib.sha256(code).hexdigest(),
        "bytes": len(code),
    }
    catalog = {"files": [asset], "summary": {"priority_matches": [asset]}}
    owner = SimpleNamespace(
        metadata={"Name": "example-tests"},
        files=[asset["path"]],
        locate_file=lambda name: installed / name,
    )
    reference_root = tmp_path / "reference"
    reference_root.mkdir()
    files = []
    for name, data in (
        tables or {"recovered.csv": b"id,value\na,4.9275633\nb,4.9275633\n"}
    ).items():
        path = reference_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    kwargs = {
        "catalog": catalog,
        "reference_root": reference_root,
        "reference_files": files,
        "exclusions": [],
        "deadline": time.time() + 30,
        "scratch": tmp_path,
        "distribution": lambda name: owner,
        "roots": [installed],
    }
    return kwargs, owner, target


def test_actual_installed_bytes_match_recovered_outputs_without_import_or_mutation(tmp_path):
    kwargs, _, target = fixture(tmp_path)
    before = target.read_bytes()
    result = build_hints(**kwargs)
    assert target.read_bytes() == before
    assert len(result["findings"]) == 1
    hint = result["findings"][0]
    assert hint["source_text"] == "expected = -4.9275633"
    assert hint["reference_path"] == "recovered.csv" and hint["matching_cells"] == 2
    assert hint["asset_sha256"] == hashlib.sha256(before).hexdigest()
    assert result["distance_is_not_grading_tolerance"]
    assert "absence is not approval" in result["scope"]
    assert not list(tmp_path.glob("tmp*")), "Temporary snapshots must close and disappear"


@pytest.mark.parametrize("change", ["bytes", "size", "owner", "record", "symlink", "outside"])
def test_unowned_changed_or_linked_assets_cannot_supply_observed_literals(tmp_path, change):
    kwargs, owner, target = fixture(tmp_path)
    asset = kwargs["catalog"]["files"][0]
    if change == "bytes":
        target.write_bytes(b"expected = 9.9275633\n")
    elif change == "size":
        asset["bytes"] += 1
    elif change == "owner":
        owner.metadata["Name"] = "other"
    elif change == "record":
        owner.files = []
    elif change == "symlink":
        moved = target.with_name("real.py")
        target.rename(moved)
        target.symlink_to(moved)
    else:
        kwargs["roots"] = [tmp_path / "unrelated-environment"]
    result = build_hints(**kwargs)
    assert not result["findings"]
    assert result["candidates"][0]["status"] in {
        "installed_asset_identity_differs",
        "installed_asset_unavailable",
    }


@pytest.mark.parametrize("matching_hash", [True, False])
def test_exclusion_does_not_clear_a_different_installed_file(tmp_path, matching_hash):
    kwargs, _, _ = fixture(tmp_path)
    asset = kwargs["catalog"]["files"][0]
    kwargs["exclusions"] = [{**asset, "sha256": asset["sha256"] if matching_hash else "0" * 64}]
    assert bool(build_hints(**kwargs)["findings"]) is not matching_hash


@pytest.mark.parametrize(
    "change",
    [
        "priority",
        "duplicate",
        "source_path",
        "reference_path",
        "reference_hash",
        "reference_link",
        "deadline",
    ],
)
def test_catalog_and_reference_provenance_or_deadline_failure_refuses_hints(tmp_path, change):
    kwargs, _, target = fixture(tmp_path)
    asset = kwargs["catalog"]["files"][0]
    if change == "priority":
        kwargs["catalog"]["summary"]["priority_matches"] = [{**asset, "sha256": "0" * 64}]
    elif change == "duplicate":
        kwargs["catalog"]["summary"]["priority_matches"].append(dict(asset))
    elif change == "source_path":
        asset["path"] = "../expected.py"
        # Invalid owned-asset evidence is a recorded discovery gap.
        assert not build_hints(**kwargs)["findings"]
        return
    elif change == "reference_path":
        kwargs["reference_files"][0]["path"] = "../reference/recovered.csv"
    elif change == "reference_hash":
        kwargs["reference_files"][0]["sha256"] = "0" * 64
    elif change == "reference_link":
        path = kwargs["reference_root"] / "recovered.csv"
        path.unlink()
        path.symlink_to(target)
    else:
        kwargs["deadline"] = time.time() - 1
    with pytest.raises((ValueError, TimeoutError)):
        build_hints(**kwargs)


def test_unsupported_formats_and_missing_literals_remain_explicit_gaps(tmp_path):
    kwargs, _, _ = fixture(
        tmp_path,
        code=b'# 4.9275633\ns = "4.9275633"\nx = 42\n',
        tables={"result.json": b'{"x": 4.9275633}'},
    )
    result = build_hints(**kwargs)
    assert not result["findings"]
    assert result["candidates"][0]["literal_count"] == 0
    assert result["reference_coverage"] == [{"path": "result.json", "status": "unsupported_format"}]


def test_deadline_during_streaming_still_closes_private_snapshot(tmp_path, monkeypatch):
    kwargs, _, target = fixture(tmp_path, code=b"expected = 4.9275633\n" * 60000)
    before = target.read_bytes()
    calls = 0

    def remaining(self):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TimeoutError("synthetic original deadline")

    monkeypatch.setattr(References, "remaining", remaining)
    with pytest.raises(TimeoutError):
        build_hints(**kwargs)
    assert target.read_bytes() == before
    assert not list(tmp_path.glob("tmp*"))


def test_helper_runs_with_standard_library_only(tmp_path):
    # -S excludes site-packages: the collector must not need httpx, pandas or a
    # scientific import merely to inspect a final empty candidate inventory.
    kwargs, _, _ = fixture(tmp_path)
    paths = {}
    for name, value in {
        "catalog": {"files": [], "summary": {"priority_matches": []}},
        "files": kwargs["reference_files"],
        "exclusions": {"files": []},
    }.items():
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_text(json.dumps(value))
    output = tmp_path / "hints.json"
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(Path(__file__).with_name("installed_asset_hints.py")),
            str(paths["catalog"]),
            str(paths["files"]),
            str(kwargs["reference_root"]),
            str(paths["exclusions"]),
            str(time.time() + 20),
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    hints = json.loads(output.read_text())
    assert hints["source"] == {
        "asset_catalog_sha256": hashlib.sha256(paths["catalog"].read_bytes()).hexdigest(),
        "reference_inventory_sha256": hashlib.sha256(paths["files"].read_bytes()).hexdigest(),
    }
    assert hints["findings"] == []


def test_real_isolated_distribution_metadata_requires_no_scientific_import(tmp_path):
    kwargs, _, target = fixture(tmp_path)
    environment = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(environment)],
        check=True,
        capture_output=True,
        timeout=20,
    )
    python = environment / "bin/python"
    site = Path(
        subprocess.check_output(
            [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True
        ).strip()
    )
    package = site / "example/tests"
    package.mkdir(parents=True)
    (package / "expected.py").write_bytes(target.read_bytes())
    (package.parent / "__init__.py").write_text(
        "raise RuntimeError('scientific import forbidden')\n"
    )
    metadata = site / "example_tests-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: Example-Tests\nVersion: 1.0\n")
    (metadata / "RECORD").write_text("example/tests/expected.py,,\nexample/__init__.py,,\n")
    paths = {}
    for name, value in {
        "catalog": kwargs["catalog"],
        "files": kwargs["reference_files"],
        "exclusions": {"files": []},
    }.items():
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_text(json.dumps(value))
    output = tmp_path / "installed-hints.json"
    result = subprocess.run(
        [
            str(python),
            str(Path(__file__).with_name("installed_asset_hints.py")),
            str(paths["catalog"]),
            str(paths["files"]),
            str(kwargs["reference_root"]),
            str(paths["exclusions"]),
            str(time.time() + 20),
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    hints = json.loads(output.read_text())
    assert len(hints["findings"]) == 1
    assert hints["findings"][0]["distribution"] == "example-tests"
    assert (package / "expected.py").read_bytes() == target.read_bytes()
