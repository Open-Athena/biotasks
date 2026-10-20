"""Publish an inspected release into the authenticated user's public namespace."""

import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError
from repo2rlenv.campaigns.release import publish_release, verify_release


def publication_target(api, repo_id, files, download=hf_hub_download):
    """Require an owned public destination; replace only manifest-managed paths."""
    owner, separator, name = repo_id.partition("/")
    if not separator or not name or "/" in name or api.whoami()["name"] != owner:
        raise ValueError("Release destination must be in the authenticated user's namespace")
    try:
        info = api.repo_info(repo_id, repo_type="dataset")
    except RepositoryNotFoundError:
        return None, []
    if info.private is not False:
        raise ValueError("Release destination must be public")
    head = info.sha
    try:
        old = json.loads(
            Path(
                download(repo_id, "release-files.json", repo_type="dataset", revision=head)
            ).read_text()
        )
    except EntryNotFoundError:
        if api.list_repo_files(repo_id, repo_type="dataset", revision=head):
            raise ValueError("Existing destination has no managed release manifest") from None
        return head, []
    if old["repo_id"] != repo_id:
        raise ValueError("Previous manifest belongs to another destination")
    obsolete = sorted(set(old["files"]) - set(files["files"]))
    if any(
        p.startswith("/") or ".." in Path(p).parts or any(char in p for char in "*?[")
        for p in obsolete
    ):
        raise ValueError("Unsafe managed path in previous release manifest")
    return head, obsolete


def main():
    staged, receipt = map(Path, sys.argv[1:])
    files = verify_release(staged)
    repo_id = files["repo_id"]
    api = HfApi()
    head, obsolete = publication_target(api, repo_id, files)

    class Replacement:
        def __init__(self):
            self.parent_commit = head

        def create_repo(self, *args, **kwargs):
            return api.create_repo(*args, **kwargs)

        def upload_folder(self, **kwargs):
            assert kwargs["repo_id"] == repo_id
            kwargs["num_threads"] = 1
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


if __name__ == "__main__":
    main()
