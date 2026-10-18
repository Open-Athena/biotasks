"""Check strict patch comparison while allowing two Git display differences."""
import argparse
import hashlib
import json
from pathlib import Path

from replay_skbio_case_commit import comparable_diff


def check(native, public):
    left = 'diff --git a/example.py b/example.py\nindex 012345678..abcdef012 100644\n--- a/example.py\n+++ b/example.py\n@@ -1,1 +1,1 @@ def example():\n-old\n+new\n'
    right = left.replace('012345678..abcdef012', '01234567..abcdef01').replace('def example():', 'class Example:')
    assert comparable_diff(left) == comparable_diff(right)
    for wrong in [right.replace('+new', '+changed'), right.replace('-1,1', '-2,1'), right.replace('example.py', 'different.py'), right.replace('100644', '100755'), right.replace('01234567', '11234567')]:
        assert comparable_diff(left) != comparable_diff(wrong)
    actual, expected = native.read_text(), public.read_text()
    assert actual != expected
    assert comparable_diff(actual) == comparable_diff(expected)
    return {'stage': 'native_and_public_diff_display_equivalence_checked_no_target_execution', 'native_raw_sha256': hashlib.sha256(native.read_bytes()).hexdigest(), 'public_raw_sha256': hashlib.sha256(public.read_bytes()).hexdigest(), 'canonical_patch_sha256': hashlib.sha256(comparable_diff(actual).encode()).hexdigest(), 'raw_renderings_differ': True, 'all_paths_modes_hunk_ranges_and_patch_lines_match': True, 'generic_changed_content_ranges_paths_modes_blob_prefixes_rejected': True, 'native_patch_rewritten': False, 'model_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-diff', type=Path, required=True)
    parser.add_argument('--public-diff', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.native_diff, args.public_diff)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
