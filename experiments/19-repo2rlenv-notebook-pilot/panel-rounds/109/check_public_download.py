"""Force an anonymous, empty-cache readback of one immutable public release."""

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from verify_hub_download import check_download


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publication", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    assert not args.receipt.exists() and not args.destination.exists()
    publication = json.loads(args.publication.read_text())
    repo_id, revision = publication["repo_id"], publication["commit_sha"]
    info = HfApi(token=False).repo_info(repo_id, repo_type="dataset", revision=revision)
    assert info.private is False and info.sha == revision
    with tempfile.TemporaryDirectory(
        prefix="anonymous-cache-", dir=args.destination.parent
    ) as cache:
        assert not list(Path(cache).iterdir())
        result = check_download(
            repo_id,
            revision,
            args.destination,
            lambda name: hf_hub_download(
                repo_id,
                name,
                repo_type="dataset",
                revision=revision,
                token=False,
                force_download=True,
                cache_dir=cache,
            ),
        )
    assert not Path(cache).exists()
    files = json.loads((args.destination / "release-files.json").read_text())["files"]
    result.update(
        observed_at=datetime.now(UTC).isoformat(),
        anonymous=True,
        empty_initial_cache=True,
        forced_download=True,
        temporary_download_cache_removed=True,
        release_files_verified=len(files),
        task_file_modes_restored_and_verified=True,
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        new_models_or_cloud_jobs=0,
    )
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
