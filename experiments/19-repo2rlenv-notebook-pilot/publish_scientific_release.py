"""Publish an inspected immutable release, replacing only prior managed paths."""

import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from repo2rlenv.campaigns.release import publish_release, verify_release

staged, receipt = map(Path, sys.argv[1:])
files = verify_release(staged)
repo_id = files["repo_id"]
assert repo_id == "gonzalobenegas/biotasks-notebook-pilot-issue-19"
api = HfApi()
assert api.whoami()["name"] == "gonzalobenegas"
info = api.repo_info(repo_id, repo_type="dataset")
assert info.private is False
head = info.sha
old = json.loads(
    Path(
        hf_hub_download(repo_id, "release-files.json", repo_type="dataset", revision=head)
    ).read_text()
)
assert old["repo_id"] == repo_id
# Only remove paths from the prior explicit release manifest that are absent in
# the replacement. Never delete unrelated Hub files or historical commits.
obsolete = sorted(set(old["files"]) - set(files["files"]))
assert all(not p.startswith("/") and ".." not in Path(p).parts for p in obsolete)
assert all(not any(char in p for char in "*?[") for p in obsolete)


class Replacement:
    def __init__(self):
        self.parent_commit = head

    def create_repo(self, *args, **kwargs):
        return api.create_repo(*args, **kwargs)

    def upload_folder(self, **kwargs):
        assert kwargs["repo_id"] == repo_id
        commit = api.upload_folder(
            **kwargs, parent_commit=self.parent_commit, delete_patterns=obsolete or None
        )
        self.parent_commit = commit.oid
        return commit

    def upload_file(self, **kwargs):
        assert kwargs["repo_id"] == repo_id
        commit = api.upload_file(**kwargs, parent_commit=self.parent_commit)
        self.parent_commit = commit.oid
        return commit

    def __getattr__(self, key):
        return getattr(api, key)


result = publish_release(staged, api=Replacement(), receipt=receipt)
print(json.dumps(result))
