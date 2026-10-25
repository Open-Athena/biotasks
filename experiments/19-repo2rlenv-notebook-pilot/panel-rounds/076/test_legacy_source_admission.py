"""Only a complete reviewed version family can change a retained resource bound."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = {
    "run_autonomous.py": "972b6315182a86988dab558ec42e63891d2dd8a380ae224253d209f476db3b12",
    "run_reference_setup.py": "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
    "reference_setup.py": "a73ff8ccfbc5281a51ba55817316f33d8d3398d4227c4218f6bf0e553c3b2c83",
}
MIXED = {
    "run_autonomous.py": "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188",
    "run_reference_setup.py": "fc83bf2ecd9f201b4bfd8c47cb07740619d09c66fc8df5a37435eb95af5b2d0b",
    "reference_setup.py": "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
}


@pytest.fixture(params=["065/reconcile_sdk_only.py", "070/closed_session_bound.py"])
def guard(request):
    spec = spec_from_file_location("guard_under_test", ROOT / request.param)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.admitted_implementation


def test_complete_legacy_version_is_admitted(guard):
    assert guard(LEGACY) == LEGACY


@pytest.mark.parametrize("name", tuple(LEGACY))
@pytest.mark.parametrize("change", ["unknown", "mixed"])
def test_unknown_or_mixed_legacy_versions_are_refused(guard, name, change):
    sources = {**LEGACY, name: "0" * 64 if change == "unknown" else MIXED[name]}
    with pytest.raises(AssertionError):
        guard(sources)


def test_extra_resource_implementation_is_refused(guard):
    with pytest.raises(AssertionError):
        guard({**LEGACY, "unreviewed_creator.py": "0" * 64})


def test_new_early_review_controller_is_not_implied_by_legacy_admission(guard):
    with pytest.raises(AssertionError):
        guard(
            {
                **LEGACY,
                "run_autonomous.py": "90037510e244c3012fd2024a092f1d327028b2fa6f2c62f42018b31a78623b4b",
            }
        )
