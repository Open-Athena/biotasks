"""Exercise extracted native filters with small synthetic diffs."""

import argparse
from pathlib import Path
from types import SimpleNamespace

from native_filters import load


def check(path):
    pipeline, native = load(path)
    pr = SimpleNamespace(
        is_draft=False, merged_at="2026-01-01", changed_files=2,
        title="Correct sequence parsing", body="Handle missing sequence names.",
    )
    assert pipeline._pre_filter(pr) is None
    pr.title = "Bump dependency version"
    assert pipeline._pre_filter(pr) == "non_bug_pr"
    pr.title = "Correct sequence parsing"
    pr.is_draft = True
    assert pipeline._pre_filter(pr) == "draft"
    source = "diff --git a/pkg/parse.py b/pkg/parse.py\n--- a/pkg/parse.py\n+++ b/pkg/parse.py\n@@ -1 +1 @@\n-old\n+new\n"
    tests = "diff --git a/tests/test_parse.py b/tests/test_parse.py\n--- a/tests/test_parse.py\n+++ b/tests/test_parse.py\n@@ -0,0 +1 @@\n+def test_missing_name(): pass\n"
    split = native["split_patch_and_test_patch"](source + tests)
    assert split == (source, tests)
    assert pipeline._structural_quality_filter(*split) is None
    assert native["_files_in_patch"](source + tests) == ["pkg/parse.py", "tests/test_parse.py"]
    assert native["_count_new_test_funcs"](tests) == 1
    assert pipeline._structural_quality_filter(source, tests.replace(
        "+def test_missing_name(): pass", "+# corrected comment"
    )) == "no_new_test_funcs"
    assert not native["_path_is_test"]("docs/tests/test_example.py")
    assert native["_path_is_test"]("src/parse_test.go")
    print("PASS: pinned native metadata, patch splitting, test-path and structural filter fixtures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", required=True, type=Path)
    check(parser.parse_args().native_source)
