"""The release replacement guards both writes and deletes only managed paths."""

import json
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.mark.parametrize("concurrent_change", [False, True])
def test_publication_parent_chain(tmp_path, monkeypatch, concurrent_change):
    repo = "gonzalobenegas/biotasks-notebook-pilot-issue-19"
    old = tmp_path / "old.json"
    old.write_text(
        json.dumps({"repo_id": repo, "files": {"old-task/data.csv": {}, "README.md": {}}})
    )
    writes = []

    class Api:
        def whoami(self):
            return {"name": "gonzalobenegas"}

        def repo_info(self, *args, **kwargs):
            return SimpleNamespace(private=False, sha="previous")

        def create_repo(self, *args, **kwargs):
            return None

        def upload_folder(self, **kwargs):
            assert kwargs["parent_commit"] == "previous"
            assert kwargs["delete_patterns"] == ["old-task/data.csv"]
            writes.append("release")
            return SimpleNamespace(oid="release")

        def upload_file(self, **kwargs):
            assert kwargs["parent_commit"] == "release"
            if concurrent_change:
                raise RuntimeError("Parent commit no longer matches")
            writes.append("registry")
            return SimpleNamespace(oid="registry")

    hub = ModuleType("huggingface_hub")
    hub.HfApi = Api
    hub.hf_hub_download = lambda *args, **kwargs: str(old)
    release = ModuleType("repo2rlenv.campaigns.release")
    release.verify_release = lambda path: {
        "repo_id": repo,
        "files": {"new-task/data.csv": {}, "README.md": {}},
    }

    def publish(directory, *, api, receipt):
        api.create_repo(repo, repo_type="dataset", private=False, exist_ok=True)
        api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(directory))
        api.upload_file(repo_id=repo, repo_type="dataset", path_in_repo="registry.json")
        return {"state": "completed"}

    release.publish_release = publish
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setitem(sys.modules, "repo2rlenv.campaigns.release", release)
    monkeypatch.setattr(sys, "argv", ["publish", str(tmp_path), str(tmp_path / "receipt.json")])
    script = Path(__file__).with_name("publish_scientific_release.py")
    if concurrent_change:
        with pytest.raises(RuntimeError, match="Parent commit"):
            runpy.run_path(str(script))
        assert writes == ["release"]
    else:
        runpy.run_path(str(script))
        assert writes == ["release", "registry"]
