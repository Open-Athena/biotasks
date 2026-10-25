"""Final inventory review binds every branch and cannot undo verified removals."""

from copy import deepcopy

import pytest
from materialization_environment import (
    binding,
    effective_exclusions,
    merge_exclusions,
    removal_receipt,
)


def excluded(path="package/tests/expected.txt"):
    return {
        "distribution": "Example-Tests",
        "path": path,
        "sha256": "a" * 64,
        "reason": "Synthetic unused answer fixture, selected by the synthetic worker",
    }


def evidence():
    base = {"files": [excluded("package/tests/original.txt")]}
    additions = [excluded()]
    effective = merge_exclusions(base, additions)
    execution = {
        "inputs": [{"path": "data.csv", "sha256": "1" * 64, "bytes": 10}],
        "reference": [{"path": "recovered.csv", "sha256": "2" * 64, "bytes": 20}],
        "oracle_outputs": [{"path": "recovered.csv", "sha256": "3" * 64, "bytes": 21}],
        "environment": {
            "asset_catalog": {"sha256": "b" * 64, "bytes": 99},
            "exclusions": effective,
            "removal_receipt": removal_receipt(effective),
        },
    }
    candidate = {
        "environment_review": {
            **binding(execution),
            "assessment": "Synthetic worker assessment, not a scientific acceptance",
            "additional_exclusions": additions,
        }
    }
    return base, candidate, execution


def test_effective_environment_contains_original_and_final_worker_declarations():
    base, candidate, execution = evidence()
    before = deepcopy((base, candidate, execution))
    effective = effective_exclusions(base, candidate, execution)
    assert len(effective["files"]) == 2
    assert (base, candidate, execution) == before


@pytest.mark.parametrize(
    "defect",
    [
        "input",
        "recovered_output",
        "oracle_output",
        "new_branch",
        "catalog",
        "receipt",
        "reintroduced_base",
        "unapplied_removal",
        "assessment",
        "review_missing",
        "execution_missing",
    ],
)
def test_review_cannot_clear_different_artifacts_or_an_unverified_environment(defect):
    base, candidate, execution = evidence()
    if defect in {"input", "recovered_output", "oracle_output"}:
        kind = {
            "input": "inputs",
            "recovered_output": "reference",
            "oracle_output": "oracle_outputs",
        }[defect]
        execution[kind][0]["sha256"] = "f" * 64
    elif defect == "new_branch":
        execution["reference"].append({"path": "another.csv", "sha256": "f" * 64, "bytes": 2})
    elif defect == "catalog":
        execution["environment"]["asset_catalog"]["sha256"] = "f" * 64
    elif defect == "receipt":
        execution["environment"]["removal_receipt"]["excluded_files_absent"] = False
    elif defect == "reintroduced_base":
        execution["environment"]["exclusions"]["files"].pop()
    elif defect == "unapplied_removal":
        candidate["environment_review"]["additional_exclusions"].append(excluded("other.txt"))
    elif defect == "assessment":
        candidate["environment_review"]["assessment"] = " "
    elif defect == "review_missing":
        candidate.pop("environment_review")
    else:
        execution.pop("environment")
    with pytest.raises((ValueError, KeyError)):
        effective_exclusions(base, candidate, execution)


@pytest.mark.parametrize("defect", ["undo", "change_hash", "duplicate", "path", "reason", "notice"])
def test_exclusions_cannot_restore_files_change_identity_or_remove_notices(defect):
    old = excluded()
    new = deepcopy(old)
    additions = [new]
    if defect == "undo":
        additions = []
    elif defect == "change_hash":
        new["sha256"] = "f" * 64
    elif defect == "duplicate":
        additions.append(deepcopy(new))
    elif defect == "path":
        new["path"] = "../expected.txt"
    elif defect == "reason":
        new["reason"] = " "
    else:
        new["path"] = "package/LICENSE.txt"
    with pytest.raises(ValueError):
        merge_exclusions(None, additions, already_applied=[old])


def test_historical_evidence_does_not_gain_a_fabricated_final_review():
    base = {"files": []}
    assert effective_exclusions(base, {}, {}) is base
