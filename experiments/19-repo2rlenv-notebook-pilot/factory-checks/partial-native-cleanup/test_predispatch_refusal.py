import copy

import pytest
from predispatch_refusal import MESSAGE, PREFIX, SOURCES, UPSTREAM, verify_refusal


def fixture():
    return {
        "pipeline": {
            "status": "infrastructure_failed",
            "failed_stage": "native",
            "error_type": "ValueError",
            "operator_interventions": 0,
        },
        "result": {
            "status": "incomplete",
            "solver": None,
            "publication_ready": False,
            "controls": [
                {
                    "agent": agent,
                    "reward": reward,
                    "passed": True,
                    "cleanup_verified": True,
                    "exception_type": None,
                }
                for agent, reward in [("oracle", 1), ("nop", 0)]
            ],
        },
        "execution": {
            "adapter_sha256": SOURCES[PREFIX + "iris_execution.py"],
            "solver_seconds": 600,
            "max_solver_attempts": 1,
            "max_trials": 3,
        },
        "task": {"agent": {"timeout_sec": 600}},
        "claims": {
            agent: {
                "trial_id": "example-native-" + agent,
                "solving": agent == "terminus-2",
                **({"cleanup_verified": True} if agent != "terminus-2" else {}),
            }
            for agent in ["oracle", "nop", "terminus-2"]
        },
        "paths": ["native/oracle/remote-job.json", "native/nop/remote-job.json"],
        "log": "\n".join(
            [
                'File "run_scientific_native.py", line 105, in run',
                'File "iris_execution.py", line 206, in run_trial',
                'File "huggingface-Repo2RLEnv-5555443/src/repo2rlenv/execution/harbor.py", line 257, in run_trial',
                "ValueError: " + MESSAGE,
            ]
        ),
        "source_hashes": dict(SOURCES),
        "upstream_sha256": UPSTREAM,
    }


def test_trace_and_exact_source_can_prove_nondispatch_without_fabricating_receipt():
    value = fixture()
    original = copy.deepcopy(value)
    result = verify_refusal(**value)
    assert value == original
    assert result["dispatch_disproven_by_original_trace_and_exact_source"]
    assert not result["original_outcome_receipt_present"]
    assert not result["scientific_acceptance_or_solver_result_inferred"]


@pytest.mark.parametrize(
    "defect",
    [
        "creator",
        "native_source",
        "upstream",
        "no_trace",
        "later_failure",
        "different_guard",
        "solver_result",
        "solver_remote_job",
        "solver_file",
        "unclean_control",
        "missing_claim",
        "extra_claim",
        "different_task_clock",
        "operator_edit",
    ],
)
def test_missing_files_alone_or_changed_execution_cannot_prove_nondispatch(defect):
    value = fixture()
    if defect == "creator":
        value["source_hashes"][PREFIX + "iris_execution.py"] = "unknown"
    elif defect == "native_source":
        value["source_hashes"][PREFIX + "run_scientific_native.py"] = "unknown"
    elif defect == "upstream":
        value["upstream_sha256"] = "unknown"
    elif defect == "no_trace":
        value["log"] = ""
    elif defect == "later_failure":
        value["log"] += "\nTimeoutError: uncertain dispatch"
    elif defect == "different_guard":
        value["log"] = value["log"].replace("line 257", "line 500")
    elif defect == "solver_result":
        value["result"]["solver"] = {"reward": 0}
    elif defect == "solver_remote_job":
        value["paths"].append("native/terminus-2/remote-job.json")
    elif defect == "solver_file":
        value["paths"].append("native/terminus-2/trial.json")
    elif defect == "unclean_control":
        value["result"]["controls"][1]["cleanup_verified"] = False
    elif defect == "missing_claim":
        del value["claims"]["nop"]
    elif defect == "extra_claim":
        value["claims"]["second-solver"] = {}
    elif defect == "different_task_clock":
        value["task"]["agent"]["timeout_sec"] = 0
    elif defect == "operator_edit":
        value["pipeline"]["operator_interventions"] = 1
    with pytest.raises(AssertionError):
        verify_refusal(**value)
