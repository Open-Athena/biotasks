"""Do not turn a timeout allowance into a generic failure-cost exemption."""

import copy
import unittest

from native_resource_record import verify_native_resource_record


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.metadata = dict(
            state="completed",
            command_returncode=0,
            trial_dispatched=True,
            command=["harbor", "--max-retries", "0"],
            exception_type="AgentTimeoutError",
            agent_timeout_sec=600,
        )
        self.result = {"exception_info": {"exception_type": "AgentTimeoutError"}}

    def test_handled_timeout(self):
        self.assertEqual(
            verify_native_resource_record("terminus-2", self.metadata, self.result),
            "AgentTimeoutError",
        )

    def test_normal_completion(self):
        metadata = {**self.metadata, "exception_type": None}
        self.assertIsNone(
            verify_native_resource_record("oracle", metadata, {"exception_info": None})
        )

    def test_other_failures_and_limits_refused(self):
        for changed in (
            {"state": "incomplete"},
            {"command_returncode": 1},
            {"trial_dispatched": False},
            {"agent_timeout_sec": 1200},
            {"exception_type": "ConnectionError"},
            {"command": ["harbor"]},
            {"command": ["harbor", "--max-retries", "1"]},
            {"command": ["harbor", "--max-retries", "0", "--max-retries", "0"]},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                verify_native_resource_record(
                    "terminus-2", {**self.metadata, **changed}, self.result
                )

    def test_non_solver_timeout_refused(self):
        with self.assertRaises(ValueError):
            verify_native_resource_record("oracle", self.metadata, self.result)

    def test_original_result_disagreement_refused(self):
        for result in (
            {"exception_info": None},
            {},
            {"exception_info": {"exception_type": "ConnectionError"}},
        ):
            with self.subTest(result=result), self.assertRaises(ValueError):
                verify_native_resource_record("terminus-2", self.metadata, result)

    def test_hidden_original_exception_refused(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["exception_type"] = None
        with self.assertRaises(ValueError):
            verify_native_resource_record("terminus-2", metadata, self.result)
