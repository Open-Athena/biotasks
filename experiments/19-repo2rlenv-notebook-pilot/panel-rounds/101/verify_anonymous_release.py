"""Use the existing verifier with explicit anonymous, empty-cache downloads."""

import argparse
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from verify_hub_download import check_download  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("publication", type=Path)
parser.add_argument("destination", type=Path)
parser.add_argument("cache", type=Path)
parser.add_argument("receipt", type=Path)
parser.add_argument("--expected-bundle", required=True)
args = parser.parse_args()
publication = json.loads(args.publication.read_text())
assert publication["state"] == "completed"
assert not args.cache.exists() and not args.receipt.exists()
args.cache.mkdir(parents=True, mode=0o700)


def download(name):
    return hf_hub_download(
        publication["repo_id"],
        name,
        repo_type="dataset",
        revision=publication["commit_sha"],
        token=False,
        cache_dir=args.cache,
        force_download=True,
        local_files_only=False,
    )


result = check_download(
    publication["repo_id"], publication["commit_sha"], args.destination, download
)
assert [row["bundle_hash"] for row in result["tasks"]] == [args.expected_bundle]
result.update(
    anonymous=True,
    token_explicitly_false=True,
    cache_initially_empty=True,
    force_download=True,
    native_bundle_identity_preserved=True,
    all_release_files_and_modes_verified=True,
)
raw = (json.dumps(result, indent=2) + "\n").encode()
args.receipt.write_bytes(raw)
assert args.receipt.read_bytes() == raw
# The complete verified download is retained; the duplicate download cache is not.
shutil.rmtree(args.cache)
print(json.dumps(result), flush=True)
