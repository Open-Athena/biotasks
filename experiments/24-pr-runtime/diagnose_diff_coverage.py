"""Diagnose one recorded mismatch without replacing the native static ledger."""

import argparse
import hashlib
import json
from pathlib import Path

from native_filters import load

ROOT = Path(__file__).resolve().parent


def main(source):
    _, native = load(source)
    path = ROOT / "inventory/pr-diffs/psychopy__psychopy/7599.diff"
    receipt = json.loads(path.with_suffix(".json").read_text())
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt["sha256"]
    diff = raw.decode()
    headers = [line for line in diff.splitlines() if line.startswith("diff --git ")]
    paths = []
    for header in headers:
        # This diagnostic is deliberately limited to this observed same-path
        # binary diff. It is not a general Git quoting/rename parser.
        left, separator, right = header.removeprefix("diff --git a/").partition(" b/")
        assert separator and left == right
        assert right.startswith("psychopy/tests/data/") and right.endswith(".png")
        paths.append(right)
    record = next(
        json.loads(line)
        for line in (ROOT / "inventory/static-assessment.jsonl").read_text().splitlines()
        if json.loads(line)["repository"] == "psychopy/psychopy"
        and json.loads(line)["number"] == 7599
    )
    native_paths = native["_files_in_patch"](diff)
    assert len(headers) == record["api_changed_files"]
    missing = sorted(set(paths) - set(native_paths))
    assert all(" " in path for path in missing)
    assert not any(line.startswith("@@") for line in diff.splitlines())
    output = {
        "repository": "psychopy/psychopy", "number": 7599,
        "diff_sha256": receipt["sha256"],
        "original_disposition": record["disposition"],
        "original_ledger_unchanged": True,
        "api_changed_files": record["api_changed_files"],
        "observed_binary_diff_headers": len(headers),
        "native_parsed_paths": native_paths,
        "paths_not_recognized_by_native_parser": missing,
        "diagnosis": (
            "The fetched diff contains all API-reported file headers. Native whitespace "
            "path matching omits PNG fixture paths containing spaces."
        ),
        "followup_disposition": "test_fixture_only_no_source_fix",
        "reason": "All changed paths are test PNG fixtures; no textual source hunks.",
        "limitations": "Case-specific diagnosis, not a general replacement diff parser.",
    }
    destination = ROOT / "evidence/diff-coverage-diagnosis.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", required=True, type=Path)
    main(parser.parse_args().native_source)
