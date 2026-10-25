"""A partial native trial is not evidence of absence after dispatch."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location("native_prefix_audit", Path(__file__).with_name("audit_prefix.py"))
module = module_from_spec(spec)
spec.loader.exec_module(module)
HARBOR_SOURCES, IRIS_SOURCE, SDK_FOLDERS = (
    module.HARBOR_SOURCES,
    module.IRIS_SOURCE,
    module.SDK_FOLDERS,
)
audit_no_dispatch = module.audit_no_dispatch


def data():
    return {
        "pipeline": {
            "status": "infrastructure_failed",
            "failed_stage": "native",
            "finished": 9,
            "stages": [
                {"name": n, "status": "incomplete" if n == "native" else "completed"}
                for n in (
                    "preparation",
                    "setup",
                    "replay",
                    "specification",
                    "construction",
                    "grading",
                    "native",
                )
            ],
        },
        "native": {
            "status": "incomplete",
            "controls": [],
            "solver": None,
            "publication_ready": False,
            "finished": 9,
        },
        "trial": {
            "agent": "oracle",
            "model": None,
            "state": "interrupted",
            "trial_id": "fixture-oracle",
        },
        "claims": [{"trial_id": "fixture-oracle", "solving": False}],
        "paths": [*(f + "/sandbox-claim.json" for f in SDK_FOLDERS), "native/oracle/trial.json"],
        "sources": {
            "patched_harbor_sha256": sorted(HARBOR_SOURCES)[0],
            "iris_execution_sha256": IRIS_SOURCE,
        },
    }


def test_original_undispatched_oracle_has_no_native_cleanup_to_invent():
    assert audit_no_dispatch(**data())["native_cleanup_applicable"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["trial"].update(command=["harbor", "run"]),
        lambda d: d["trial"].update(trial_dispatched=True),
        lambda d: d["sources"].update(patched_harbor_sha256="unknown"),
        lambda d: d["sources"].update(iris_execution_sha256="unknown"),
        lambda d: d["paths"].append("native/oracle/remote-job.json"),
        lambda d: d["paths"].append("native/nop/trial.json"),
        lambda d: d["paths"].append("another-stage/sandbox-claim.json"),
        lambda d: d["native"]["controls"].append({"reward": 1}),
        lambda d: d["claims"].append({"trial_id": "another", "solving": False}),
        lambda d: d["claims"][0].update(solving=True),
        lambda d: d["claims"][0].update(trial_id="another"),
    ],
)
def test_ambiguous_or_started_execution_cannot_claim_no_native_resources(mutation):
    value = deepcopy(data())
    mutation(value)
    with pytest.raises(AssertionError):
        audit_no_dispatch(**value)
