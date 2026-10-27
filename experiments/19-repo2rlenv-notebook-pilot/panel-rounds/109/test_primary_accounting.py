"""Do not release resource holds from a wrong role, source or terminal claim."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "070"))
from closed_session_bound import admitted_implementation  # noqa: E402
from primary_accounting import check_bootstrap_role, check_primary_terminal  # noqa: E402


@pytest.mark.parametrize("primary", [False, True])
def test_each_original_archive_role_accepts_its_actual_bootstrap(primary):
    status = {"completed": primary, "error_type": None if primary else "TimeoutExpired"}
    check_bootstrap_role(status, primary=primary)
    with pytest.raises(AssertionError):
        check_bootstrap_role(status, primary=not primary)


@pytest.mark.parametrize(
    "completed,error",
    [
        (False, None),
        (True, "TimeoutExpired"),
        (False, "ConnectionError"),
        (1, None),
        (0, "TimeoutExpired"),
    ],
)
def test_uncertain_or_unexpected_bootstrap_does_not_fit_either_role(completed, error):
    for primary in (False, True):
        with pytest.raises(AssertionError):
            check_bootstrap_role({"completed": completed, "error_type": error}, primary=primary)


def test_latest_typed_observation_must_be_success_for_this_original_claim():
    records = [
        {
            "observed_at": "2026-10-27T20:00:00Z",
            "terminal": False,
            "state": "RUNNING",
            "claim_sha256": "a" * 64,
        },
        {
            "observed_at": "2026-10-27T21:00:00Z",
            "terminal": True,
            "state": "SUCCEEDED",
            "claim_sha256": "a" * 64,
        },
    ]
    check_primary_terminal(records, claim_sha256="a" * 64)
    with pytest.raises(AssertionError):
        check_primary_terminal(records, claim_sha256="b" * 64)
    records[-1]["state"] = "RUNNING"
    with pytest.raises(AssertionError):
        check_primary_terminal(records, claim_sha256="a" * 64)


@pytest.mark.parametrize(
    "state,terminal",
    [
        ("FAILED", True),
        ("KILLED", True),
        ("RUNNING", False),
        ("SUCCEEDED", False),
        ("SUCCEEDED", "true"),
    ],
)
def test_nonterminal_or_failed_jobs_cannot_be_priced_as_primary_success(state, terminal):
    with pytest.raises(AssertionError):
        check_primary_terminal(
            [
                {
                    "observed_at": "2026-10-27T21:00:00Z",
                    "terminal": terminal,
                    "state": state,
                    "claim_sha256": "a" * 64,
                }
            ],
            claim_sha256="a" * 64,
        )


@pytest.mark.parametrize("profile", ["108/runtime-identity-224.json", "109/runtime-identity.json"])
def test_exact_already_validated_resource_families_are_admitted(profile):
    runtime = json.loads((HERE.parent / profile).read_text())["runtime_files"]
    sources = {
        name: runtime["experiments/19-repo2rlenv-notebook-pilot/" + name]
        for name in ("run_autonomous.py", "run_reference_setup.py", "reference_setup.py")
    }
    assert admitted_implementation(sources) == sources
    for name in sources:
        with pytest.raises(AssertionError):
            admitted_implementation({**sources, name: "0" * 64})


def test_new_controller_family_changes_only_final_export_not_resource_lifecycle():
    path = EXPERIMENT / "factory-checks/primary-snapshot/prove_boundary.py"
    spec = importlib.util.spec_from_file_location("primary_accounting_source_boundary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = (EXPERIMENT / "run_autonomous.py").read_bytes()
    assert (
        hashlib.sha256(current).hexdigest()
        == "2f8994be3c6f8cad3e8a9f8599ee3e5a97d32f2093720bd9bdc3ce313516e240"
    )
    module.prove_controller(module.original("run_autonomous.py"), current)
