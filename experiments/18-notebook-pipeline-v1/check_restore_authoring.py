"""Small offline regressions for evidence assembly; no biology or cloud access."""

import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from restore_authoring import restore


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        for name, content in files.items():
            target.writestr(name, content)
    return output.getvalue()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class AssemblyChecks(unittest.TestCase):
    def test_empty_verified_construction_reaches_review_without_trials(self):
        from native_suite import run_suite
        from biotasks.factory_controller import NativeEvidence, WorkerEvidence, decide

        raw = archive({"construction-report.json": b"{}"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = restore(
                lambda *_: io.BytesIO(raw), "remote", root / "native", sha(raw), [],
                require_task=False, deleted_inputs=[], expected_task_manifest=[],
            )

            def forbidden(*args):
                self.fail("Empty construction must not launch native trials")

            result = run_suite(
                workspace, {"n_attempts": 1, "retry": {"max_retries": 0}}, root / "records",
                {"maximum_trials": 7, "trial_timeout_seconds": 1800,
                 "reference_timeout_seconds": 600}, forbidden, forbidden, forbidden,
            )
            self.assertFalse((workspace / "task").exists())
            self.assertEqual(result["status"], "not_runnable")
            evidence = NativeEvidence.from_records(workspace, root / "records")
            worker = WorkerEvidence("construction", "succeeded", "request_cap", True,
                                    result["candidate_sha256"])
            self.assertEqual(decide(worker, evidence, workspace=workspace).action, "review")
            with self.assertRaisesRegex(ValueError, "No candidate task"):
                restore(lambda *_: io.BytesIO(raw), "remote", root / "baseline", sha(raw), [])
            with self.assertRaisesRegex(ValueError, "differs from final parent manifest"):
                restore(lambda *_: io.BytesIO(raw), "remote", root / "mismatch", sha(raw), [],
                        require_task=False, expected_task_manifest=[{
                            "path": "instruction.md", "size": 1, "sha256": sha(b"x")}])

    def test_repair_retains_parent_inputs_and_overlays_changed_code(self):
        initial = archive({"task/instruction.md": b"v1"})
        repaired = archive({"task/instruction.md": b"v2"})
        files = {
            "first/inputs.zip": initial,
            "first/workspace/task/environment/data": b"observed",
            "second/inputs.zip": repaired,
            "second/workspace/task/tests/test.sh": b"grader",
        }
        entries = [
            [{"path": "task/environment/data", "size": 8, "sha256": sha(b"observed")}],
            [{"path": "task/tests/test.sh", "size": 6, "sha256": sha(b"grader")}],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            first = restore(
                lambda uri, mode: io.BytesIO(files[uri]),
                "first",
                Path(tmp) / "v1",
                sha(initial),
                entries[0],
            )
            second = restore(
                lambda uri, mode: io.BytesIO(files[uri]),
                "second",
                Path(tmp) / "v2",
                sha(repaired),
                entries[1],
                first,
            )
            self.assertEqual((second / "task/environment/data").read_bytes(), b"observed")
            self.assertEqual((second / "task/instruction.md").read_bytes(), b"v2")
            self.assertEqual((second / "task/tests/test.sh").read_bytes(), b"grader")

    def test_native_and_review_replay_apply_deletions_and_check_final_manifest(self):
        raw = archive({"task/instruction.md": b"keep", "task/obsolete.py": b"delete"})
        final = [{"path": "instruction.md", "size": 4, "sha256": sha(b"keep")}]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = restore(
                lambda *_: io.BytesIO(raw),
                "remote",
                Path(tmp) / "native",
                sha(raw),
                [],
                deleted_inputs=["task/obsolete.py"],
                expected_task_manifest=final,
            )
            self.assertFalse((workspace / "task/obsolete.py").exists())
            with self.assertRaisesRegex(ValueError, "differs from final parent manifest"):
                restore(
                    lambda *_: io.BytesIO(raw),
                    "remote",
                    Path(tmp) / "wrong",
                    sha(raw),
                    [],
                    deleted_inputs=[],
                    expected_task_manifest=final,
                )

    def test_corrupt_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "checksum"):
            restore(
                lambda uri, mode: io.BytesIO(b"wrong"),
                "source",
                Path(tmp) / "out",
                sha(b"right"),
                [],
            )

    def test_archive_cannot_escape_assembly(self):
        data = archive({"../escaped": b"no"})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "escapes"):
                restore(
                    lambda uri, mode: io.BytesIO(data), "source", Path(tmp) / "out", sha(data), []
                )
            self.assertFalse((Path(tmp) / "out/escaped").exists())


if __name__ == "__main__":
    unittest.main()
