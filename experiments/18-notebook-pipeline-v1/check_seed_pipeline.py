"""Offline fixed-stage orchestration check with simulated model/native outcomes."""

import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# These adapters are not exercised by this offline routing test.
sys.modules.setdefault("fsspec", types.ModuleType("fsspec"))
zcode = types.ModuleType("zcode_smoke")
zcode.export_files = lambda path: (list(path.rglob("*")), [])
sys.modules["zcode_smoke"] = zcode

from seed_pipeline_worker import SeedPipeline, write_json  # noqa: E402

from biotasks.factory_acceptance import AUDIT_REQUIREMENTS  # noqa: E402
from biotasks.factory_controller import NativeEvidence  # noqa: E402
from biotasks.factory_native import candidate_hash, file_hash  # noqa: E402


class SimulatedPipeline(SeedPipeline):
    def __init__(self, root, reject=False, defect=False):
        self.root = root
        self.plan = {"workflow_version": 2, "input_zip_sha256": file_hash(root / "inputs.zip")}
        self.reject, self.defect = reject, defect
        self.calls = []
        self.accepted = False

    def upload(self, *args):
        pass

    def checkpoint(self, status, **extra):
        return {"status": status, **extra}

    def model(self, slot, workspace=None, native=None):
        self.calls.append(slot)
        target = self.root / slot / "author-workspace"
        if workspace is None:
            target.mkdir(parents=True)
        else:
            shutil.copytree(workspace, target)
        (target / "task").mkdir(exist_ok=True)
        (target / "task/instruction.md").write_text("Test fixture; no biology execution")
        (target / "evidence.md").write_text("Simulated audit evidence")
        write_json(
            target / "task/grading-contract.json",
            {
                "schema_version": 1,
                "subgoals": [
                    {"id": "a", "weight": 0.5, "description": "First", "depends_on": []},
                    {"id": "b", "weight": 0.5, "description": "Second", "depends_on": ["a"]},
                ],
            },
        )
        if slot.startswith("review"):
            write_json(
                target / "review/report.json",
                {
                    "schema_version": 1,
                    "disposition": "ready_for_validation",
                    "findings": [],
                    "checks_performed": [],
                    "checks_pending": [],
                    "acceptance_checks": {
                        name: {
                            "status": "satisfied",
                            "rationale": "Test fixture",
                            "evidence_paths": ["evidence.md"],
                        }
                        for name in AUDIT_REQUIREMENTS
                    },
                },
            )
        return target, {"outcome": "worker_finished"}

    def harbor(self, slot, parent_slot):
        self.calls.append(slot)
        records = self.root / slot / "records"
        if slot != "baseline":
            reference = records / "native/reference"
            reference.mkdir(parents=True)
            row = {
                "backend_disk_gib": 10,
                "backend_metrics": [{"disk_total": 10 * 1024**3, "disk_used": 1000}],
                "measurements": {"memory.peak": "1048576"},
            }
            (reference / "sandbox-resources.jsonl").write_text((json.dumps(row) + "\n") * 2)
        else:
            trial = records / "jobs/baseline/task/attempts/000"
            write_json(trial / "result.json", {"verifier_result": {"rewards": {"reward": 0.5}}})
            write_json(
                trial / "verifier/grade.json", {"subgoals": {"a": True, "b": False}, "reward": 0.5}
            )
        return records

    def native_evidence(self, workspace, directory):
        status = (
            "task_defect"
            if self.defect and "native_after_construction" in str(directory)
            else "passed"
        )
        return NativeEvidence(candidate_hash(workspace), status)


class PipelineChecks(unittest.TestCase):
    def run_case(self, reject=False, defect=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inputs.zip").write_bytes(b"frozen source")
            pipeline = SimulatedPipeline(root, reject, defect)
            with (
                patch(
                    "seed_pipeline_worker.proposal_action",
                    return_value="rejected" if reject else "construction",
                ),
                patch.object(NativeEvidence, "from_records", side_effect=pipeline.native_evidence),
                patch(
                    "biotasks.factory_acceptance.assess_saved_suite",
                    return_value={"status": "passed", "cases": [{"id": "reference"}]},
                ),
            ):
                outcome = pipeline.run()
            return outcome, pipeline.calls

    def test_rejected_seed_stops_before_construction(self):
        outcome, calls = self.run_case(reject=True)
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(calls, ["specification"])

    def test_valid_task_gets_one_fresh_baseline_even_if_not_fully_solved(self):
        outcome, calls = self.run_case()
        self.assertEqual(outcome["status"], "accepted")
        self.assertFalse(outcome["full_success"])
        self.assertEqual(
            calls,
            ["specification", "construction", "native_after_construction", "review", "baseline"],
        )

    def test_native_defect_routes_through_one_glm_repair_and_fresh_audit(self):
        outcome, calls = self.run_case(defect=True)
        self.assertEqual(outcome["status"], "accepted")
        self.assertEqual(
            calls,
            [
                "specification",
                "construction",
                "native_after_construction",
                "review",
                "repair",
                "native_after_repair",
                "review_after_repair",
                "baseline",
            ],
        )


if __name__ == "__main__":
    unittest.main()
