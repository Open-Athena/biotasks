"""Re-fetch the primary source notices for an exact-byte publication review."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("review", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert not args.output.exists()
review = json.loads(args.review.read_text())
assert review["current_notebook_license_and_distribution_texts_verified"]
assert review["historical_flag_superseded_for_these_exact_inputs_by_this_review"]
documents = []
for row in review["primary_sources"]:
    url = urlsplit(row["url"])
    assert url.netloc == "github.com"
    owner, repo, marker, ref, *parts = url.path.strip("/").split("/")
    assert marker == "blob" and parts
    raw = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/contents/{'/'.join(parts)}?ref={ref}",
            "-H",
            "Accept: application/vnd.github.raw+json",
        ]
    )
    assert len(raw) == row["bytes"]
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    documents.append({**row, "fresh_primary_bytes_verified": True})
    if row["name"] == "pinned-data-policy":
        text = raw.decode()
        start = text.index("Using test data files")
        policy = text[start:]
        assert "GNU Public Licence v2" in policy and "not confidential" in policy
        print(policy[:4000])
    if row["name"] == "testsuite-readme":
        print(raw.decode())
result = {
    "checked_at": datetime.now(UTC).isoformat(),
    "review_sha256": hashlib.sha256(args.review.read_bytes()).hexdigest(),
    "fresh_primary_sources": documents,
    "all_primary_source_hashes_and_sizes_match": True,
    "historical_unassessed_flag_is_superseded_for_exact_reviewed_inputs": True,
    "input_origin": review["input_origin"],
    "scope": "Original public simulation inputs, exact bytes and full retained notices; no new rights or blanket relicense inferred.",
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
