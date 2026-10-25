"""A new or deleted prompt cannot disappear from the reviewed runtime delta."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location("source_freezer", Path(__file__).with_name("freeze_source_run.py"))
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


def test_additions_removals_and_edits_are_all_reviewed():
    current = {"runtime.py": "new", "new-prompt.md": "added", "same.py": "same"}
    previous = {"runtime.py": "old", "old-prompt.md": "removed", "same.py": "same"}
    paths = ["runtime.py", "new-prompt.md", "old-prompt.md"]
    assert module.reviewed_runtime_delta(current, previous, paths) == (
        sorted(paths),
        ["new-prompt.md"],
        ["old-prompt.md"],
    )


@pytest.mark.parametrize(
    "expected", [[], ["runtime.py"], ["new.md", "new.md"], ["new.md", "unseen.md"]]
)
def test_missing_extra_or_duplicate_review_does_not_admit_a_new_file(expected):
    with pytest.raises(AssertionError):
        module.reviewed_runtime_delta(
            {"runtime.py": "same", "new.md": "new"}, {"runtime.py": "same"}, expected
        )


@pytest.mark.parametrize("name", ["../outside", "/absolute", "a//b", "a/../b", "."])
def test_unsafe_paths_are_not_a_runtime_identity(name):
    with pytest.raises(AssertionError):
        module.reviewed_runtime_delta({name: "content"}, {}, [name])


def test_identical_runtimes_require_no_changes():
    assert module.reviewed_runtime_delta({"same.py": "same"}, {"same.py": "same"}, []) == (
        [],
        [],
        [],
    )
