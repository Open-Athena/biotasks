"""Minimal general targeting change; preserve reset/metadata path extraction."""
from pathlib import Path
import difflib
import hashlib

ROOT = Path(__file__).resolve().parent
HELPER = '''def _runnable_test_files_in_patch(unified_diff: str) -> list[str]:
    """Return changed destination paths that survive application of the patch.

    Only inspect diff metadata before the first hunk. Hunk contents can contain
    text resembling a deletion header and must not affect path selection.
    Keep _files_in_patch unchanged for reset, cleanup and inventory consumers.
    """
    matches = list(_DIFF_HEADER_RE.finditer(unified_diff))
    result: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(unified_diff)
        block = unified_diff[match.end():end]
        deleted = False
        for line in block.splitlines():
            if line.startswith("@@"):
                break
            if line.startswith("deleted file mode ") or line == "+++ /dev/null":
                deleted = True
                break
        path = match.group(2)
        if not deleted and path not in result:
            result.append(path)
    return result


'''


def main():
    source = ROOT/'upstream/pipelines/pr_runtime.py'
    old = source.read_text()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '0b748a897f1802fcaf4b59ab7ed54092c8715745b5dff14813c6389b1e134535'
    new = old.replace('def _files_in_patch(unified_diff: str)', HELPER+'def _files_in_patch(unified_diff: str)', 1)
    # Only the two call sites feeding target selection change. Export reset,
    # source-file filters and metadata still include deleted paths.
    for indentation in (24, 12):
        anchor = ' '*indentation+'_files_in_patch(test_patch),'
        assert new.count(anchor+'\n') == 1
        new = new.replace(anchor+'\n', ' '*indentation+'_runnable_test_files_in_patch(test_patch),\n')
    (ROOT/'candidate/pr_runtime_targeting.py').write_text(new)
    patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
        fromfile='a/src/repo2rlenv/pipelines/pr_runtime.py',
        tofile='b/src/repo2rlenv/pipelines/pr_runtime.py'))
    (ROOT/'deleted-targets.patch').write_text(patch)
    print('Candidate SHA256:', hashlib.sha256(new.encode()).hexdigest())


if __name__ == '__main__':
    main()
