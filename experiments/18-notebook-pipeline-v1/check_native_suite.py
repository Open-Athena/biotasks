"""Exercise native orchestration and evidence ordering without cloud or biology."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_suite import run_suite

from biotasks.factory_native import assess_saved_suite
from biotasks.factory_controller import NativeEvidence, WorkerEvidence, decide


class NativeSuiteChecks(unittest.TestCase):
    def test_static_defect_retains_identity_and_routes_to_glm_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task").mkdir()
            (root / "task/instruction.md").write_text("Incomplete infrastructure fixture")

            def forbidden(*args):
                raise AssertionError("Static failure must not launch a trial or cleanup")

            result = run_suite(
                root, {"n_attempts": 1, "retry": {"max_retries": 0}}, root / "output",
                {"maximum_trials": 7, "trial_timeout_seconds": 1800,
                 "reference_timeout_seconds": 600}, forbidden, forbidden, forbidden,
            )
            self.assertEqual(result["status"], "not_runnable")
            evidence = NativeEvidence.from_records(root, root / "output")
            worker = WorkerEvidence("construction", "succeeded", "worker_finished", True,
                                    result["candidate_sha256"])
            self.assertEqual(decide(worker, evidence, workspace=root).action, "review")
            (root / "task/instruction.md").write_text("Changed after the static check")
            with self.assertRaisesRegex(ValueError, "different candidate"):
                NativeEvidence.from_records(root, root / "output")

    def run_fixture(self, root, *, changed_grade=False, storage_error=False):
        events = []
        cases = [
            {
                "id": kind,
                "kind": kind,
                "artifacts": [],
                "expected_subgoals": {"a": kind == "reference", "b": kind == "reference"},
            }
            for kind in ["reference", "empty"]
        ]
        plan = {
            "cases": cases,
            "weights": {"a": 0.5, "b": 0.5},
            "plan_sha256": "a" * 64,
            "contract_sha256": "b" * 64,
        }

        def trial(case_root, timeout):
            events.append((case_root.name, "execute"))
            config = json.loads((case_root / "harbor-job.json").read_text())
            self.assertEqual(config["n_attempts"], 1)
            self.assertEqual(config["retry"]["max_retries"], 0)
            self.assertNotIn("model_name", config["agents"][0])
            expected = json.loads((case_root / "expected.json").read_text())
            values = expected["expected_subgoals"]
            if changed_grade and case_root.name == "empty":
                values = {"a": True, "b": False}
            reward = sum(values.values()) / 2
            result_root = case_root / "jobs/job/task/attempts/000"
            result_root.mkdir(parents=True)
            agent = "oracle" if case_root.name == "reference" else "artifact-control"
            (result_root / "result.json").write_text(
                json.dumps(
                    {
                        "agent_info": {"name": agent},
                        "verifier_result": {"rewards": {"reward": reward}},
                    }
                )
            )
            (result_root / "verifier").mkdir()
            (result_root / "verifier/grade.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "subgoals": values,
                        "reward": reward,
                        "full_success": all(values.values()),
                    }
                )
            )
            probe = {
                "network_denied": True,
                "inference_credentials_present": False,
                "gpu_devices": [],
                "resources": {"cpu.max": "400000 100000", "memory.max": "8589934592"},
            }
            (case_root / "network-preflights.jsonl").write_text(
                "".join(json.dumps({"id": name, **probe}) + "\n" for name in ("task", "verifier"))
            )
            (case_root / "sandbox-resources.jsonl").write_text(
                "".join(
                    json.dumps({"id": name, "requested_storage_mb": 10240}) + "\n"
                    for name in ("task", "verifier")
                )
            )

        def persist(case_root, case_id):
            events.append((case_id, "persist"))
            if storage_error:
                raise OSError("Read-back failed")

        def cleanup(case_root):
            self.assertEqual(events[-1], (case_root.name, "persist"))
            events.append((case_root.name, "cleanup"))
            (case_root / "cleanup.json").write_text('[{"deleted": true}, {"deleted": true}]')

        with patch("native_suite.native_plan", return_value=plan):
            try:
                result = run_suite(
                    root,
                    {"n_attempts": 1, "retry": {"max_retries": 0}},
                    root / "output",
                    {
                        "maximum_trials": 7,
                        "trial_timeout_seconds": 1800,
                        "reference_timeout_seconds": 600,
                    },
                    trial,
                    persist,
                    cleanup,
                )
            finally:
                if storage_error:
                    self.assertNotIn(("reference", "cleanup"), events)
        with patch("biotasks.factory_native.native_plan", return_value=plan):
            replayed = assess_saved_suite(root, root / "output")
        self.assertEqual(replayed["status"], result["status"])
        self.assertEqual(
            events,
            [
                (kind, action)
                for kind in ["reference", "empty"]
                for action in ["execute", "persist", "cleanup", "persist"]
            ],
        )
        return result

    def test_fresh_cases_preserved_before_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_fixture(Path(tmp))
            self.assertEqual(result["status"], "passed")
            self.assertFalse(result["disk_quota_verified"])

    def test_wrong_control_outcome_is_task_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_fixture(Path(tmp), changed_grade=True)
            self.assertEqual(result["status"], "task_defect")

    def test_storage_failure_never_discards_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(OSError):
            self.run_fixture(Path(tmp), storage_error=True)


if __name__ == "__main__":
    unittest.main()
