"""Only sealed, completed, original-backed publication views can be consolidated."""

import hashlib
import json
from collections import defaultdict

import pytest
from consolidate_publication_views import publication_views
from readback_cache import identity


def make_view(tmp_path):
    publications, records = tmp_path / "publication", tmp_path / "records"
    files = publications / "001/attempt-001/evidence"
    files.mkdir(parents=True)
    receipt = records / "001/publication.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"state": "completed"}))
    raw = b"a" * (1024 * 1024)
    original = tmp_path / "original"
    original.write_bytes(raw)
    view = files / "evidence.bin"
    view.write_bytes(raw)
    row = {
        "path": "evidence.bin",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "mode": original.stat().st_mode & 0o777,
    }
    manifest = json.dumps({"files": [row]}).encode()
    (files / "export-manifest.json").write_bytes(manifest)
    groups = defaultdict(list, {(original.stat().st_dev, *identity(row)): [(original, row)]})
    manifests = {"001": hashlib.sha256(manifest).hexdigest()}
    return publications, records, groups, manifests, view, receipt


def test_matching_completed_view_keeps_original_first(tmp_path):
    publications, records, groups, manifests, view, _ = make_view(tmp_path)
    result = publication_views(publications, records, groups, manifests)
    assert result["001/attempt-001/evidence"]["large_paths"] == 1
    paths = next(iter(groups.values()))
    assert paths[0][0].name == "original" and paths[1][0] == view
    assert paths[0][0].stat().st_ino != view.stat().st_ino  # collection never mutates


@pytest.mark.parametrize("defect", ["manifest", "symlink", "missing_original", "mode"])
def test_uncertain_original_or_view_cannot_be_selected(tmp_path, defect):
    publications, records, groups, manifests, view, _ = make_view(tmp_path)
    if defect == "manifest":
        manifests["001"] = "0" * 64
    elif defect == "symlink":
        original = next(iter(groups.values()))[0][0]
        view.unlink()
        view.symlink_to(original)
    elif defect == "missing_original":
        groups.clear()
    else:
        view.chmod(0o600)
    with pytest.raises(AssertionError):
        publication_views(publications, records, groups, manifests)


def test_unpublished_work_is_not_collected(tmp_path):
    publications, records, groups, manifests, _, receipt = make_view(tmp_path)
    receipt.write_text(json.dumps({"state": "staged"}))
    assert publication_views(publications, records, groups, manifests) == {}
    assert len(next(iter(groups.values()))) == 1
