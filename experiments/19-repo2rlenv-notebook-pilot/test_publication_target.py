"""Publication must not replace unrelated datasets or remove unmanaged files."""

import json
from types import SimpleNamespace

import httpx
import pytest
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError
from publish_scientific_release import publication_target


class API:
    def __init__(self, *, missing=False, private=False):
        self.missing = missing
        self.private = private

    def whoami(self):
        return {"name": "owner"}

    def repo_info(self, *args, **kwargs):
        if self.missing:
            raise RepositoryNotFoundError(
                "missing",
                response=httpx.Response(404, request=httpx.Request("GET", "https://example.org")),
            )
        return SimpleNamespace(private=self.private, sha="frozen-head")

    def list_repo_files(self, *args, **kwargs):
        return ["unrelated.txt"]


def test_owned_new_public_destination():
    assert publication_target(API(missing=True), "owner/new", {"files": {}}) == (None, [])
    with pytest.raises(ValueError, match="namespace"):
        publication_target(API(), "other/new", {"files": {}})
    with pytest.raises(ValueError, match="public"):
        publication_target(API(private=True), "owner/new", {"files": {}})


def test_only_prior_managed_paths_removed(tmp_path):
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps({"repo_id": "owner/new", "files": {"keep": {}, "old": {}}}))
    head, obsolete = publication_target(
        API(), "owner/new", {"files": {"keep": {}, "new": {}}}, lambda *a, **k: previous
    )
    assert head == "frozen-head" and obsolete == ["old"]
    previous.write_text(json.dumps({"repo_id": "owner/new", "files": {"*.txt": {}}}))
    with pytest.raises(ValueError, match="Unsafe"):
        publication_target(API(), "owner/new", {"files": {}}, lambda *a, **k: previous)


def test_unmanaged_existing_dataset_rejected():
    def missing(*args, **kwargs):
        raise EntryNotFoundError("missing")

    with pytest.raises(ValueError, match="no managed release manifest"):
        publication_target(API(), "owner/new", {"files": {}}, missing)
