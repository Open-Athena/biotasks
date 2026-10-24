"""Post-native notices are pinned evidence, never replacements for task controls."""

import hashlib
import json

import pytest
from release_metadata import additional_release_evidence


def config(tmp_path, value=None):
    path = tmp_path / "notices.json"
    path.write_text(json.dumps(value if value is not None else {"notice": "Original terms"}))
    return {
        "release_metadata": {
            "evidence_documents": {
                "publication-notices.json": {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            }
        }
    }


def test_pinned_notices_are_exact_and_default_releases_do_not_change(tmp_path):
    declaration = config(tmp_path)
    original = json.loads(json.dumps(declaration))
    assert additional_release_evidence(declaration, reserved={"grading-controls.json"}) == {
        "publication-notices.json": {"notice": "Original terms"}
    }
    assert declaration == original
    assert additional_release_evidence({}, reserved={"grading-controls.json"}) == {}


@pytest.mark.parametrize(
    "name",
    ["grading-controls.json", "GRADING-CONTROLS.JSON", "../notices.json", "a/b.json", "a.txt"],
)
def test_cannot_replace_controls_or_escape_evidence_directory(tmp_path, name):
    declaration = config(tmp_path)
    documents = declaration["release_metadata"]["evidence_documents"]
    documents[name] = documents.pop("publication-notices.json")
    with pytest.raises(ValueError, match="replace existing"):
        additional_release_evidence(declaration, reserved={"grading-controls.json"})


def test_case_aliases_are_not_distinct_documents(tmp_path):
    declaration = config(tmp_path)
    documents = declaration["release_metadata"]["evidence_documents"]
    documents["Publication-Notices.json"] = documents["publication-notices.json"]
    with pytest.raises(ValueError, match="replace existing"):
        additional_release_evidence(declaration, reserved={})


def test_changed_notices_cannot_inherit_reviewed_hash(tmp_path):
    declaration = config(tmp_path)
    (tmp_path / "notices.json").write_text('{"notice":"Changed terms"}')
    with pytest.raises(ValueError, match="reviewed hash"):
        additional_release_evidence(declaration, reserved={})


@pytest.mark.parametrize("value", [[], ["notice"], {}, "notice", None])
def test_only_nonempty_objects_are_evidence(tmp_path, value):
    declaration = config(tmp_path)
    path = tmp_path / "notices.json"
    path.write_text(json.dumps(value))
    declaration["release_metadata"]["evidence_documents"]["publication-notices.json"]["sha256"] = (
        hashlib.sha256(path.read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="nonempty JSON object"):
        additional_release_evidence(declaration, reserved={})


def test_symlink_and_unpinned_documents_are_rejected(tmp_path):
    declaration = config(tmp_path)
    item = declaration["release_metadata"]["evidence_documents"]["publication-notices.json"]
    alias = tmp_path / "alias.json"
    alias.symlink_to(tmp_path / "notices.json")
    item["path"] = str(alias)
    with pytest.raises(ValueError, match="regular document"):
        additional_release_evidence(declaration, reserved={})
    item.pop("sha256")
    with pytest.raises(ValueError, match="explicit path and SHA256"):
        additional_release_evidence(declaration, reserved={})
