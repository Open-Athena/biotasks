"""Offline regression checks for exact candidate and evidence handoffs."""

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from prepare_worker_handoff import prepare, unpack_handoff


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(path, data):
    return {"path": path, "size": len(data), "sha256": sha(data)}


def inputs(root, files):
    output = root / "inputs.zip"
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.read_bytes()


def parent_record(root, raw):
    records = root / "parent-records"
    records.mkdir()
    (records / "result.json").write_bytes(raw)
    return entry("result.json", raw)


class HandoffChecks(unittest.TestCase):
    def test_bootstrap_rejects_descriptor_swap_and_extraneous_worker_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'{"record_files": []}'
            envelope = root / "handoff.zip"
            with zipfile.ZipFile(envelope, "w") as archive:
                archive.writestr("parent-restore.json", raw)
                archive.writestr("_biotasks_smoke.py", b"unauthorized code")
            spec = {
                "input_zip_sha256": sha(envelope.read_bytes()),
                "predecessor": {"artifact_receipt_sha256": "0" * 64},
            }
            with self.assertRaisesRegex(ValueError, "descriptor differs"):
                unpack_handoff(root, spec)
            spec["predecessor"]["artifact_receipt_sha256"] = sha(raw)
            with self.assertRaisesRegex(ValueError, "Unexpected files"):
                unpack_handoff(root, spec)
            self.assertFalse((root / "_biotasks_smoke.py").exists())

    def test_bootstrap_restores_parent_input_from_remote_and_verifies_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("task/instruction.md", b"parent candidate")
            original = buffer.getvalue()
            record = b"parent result"
            raw = json.dumps(
                {
                    "artifact_prefix": "remote/parent",
                    "input_zip_sha256": sha(original),
                    "generated_manifest": [],
                    "deleted_inputs": [],
                    "task_manifest": [entry("instruction.md", b"parent candidate")],
                    "record_files": [entry("result.json", record)],
                }
            ).encode()
            envelope = root / "handoff.zip"
            with zipfile.ZipFile(envelope, "w") as archive:
                archive.writestr("parent-restore.json", raw)
                archive.writestr("parent-records/result.json", record)
            spec = {
                "input_zip_sha256": sha(envelope.read_bytes()),
                "predecessor": {"artifact_receipt_sha256": sha(raw)},
            }
            parent = unpack_handoff(root, spec)

            def remote(uri, mode):
                self.assertEqual(uri, "remote/parent/inputs.zip")
                return io.BytesIO(original)

            prepared, _ = prepare(remote, root, parent)
            with zipfile.ZipFile(prepared) as archive:
                self.assertEqual(archive.read("task/instruction.md"), b"parent candidate")

    def test_repeated_handoff_preserves_history_and_applies_deletions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_receipt = b'{"stage": "earlier"}'
            raw = inputs(
                root,
                {
                    "task/instruction.md": b"unchanged",
                    "task/removed.txt": b"delete me",
                    "previous-run/handoff.json": old_receipt,
                    "previous-run/result.json": b"previous result",
                },
            )
            descriptor = {
                "artifact_prefix": "remote/parent",
                "input_zip_sha256": sha(raw),
                "generated_manifest": [entry("task/tests/test.sh", b"grader")],
                "deleted_inputs": ["task/removed.txt"],
                "task_manifest": [
                    entry("instruction.md", b"unchanged"),
                    entry("tests/test.sh", b"grader"),
                ],
                "record_files": [parent_record(root, b"latest result")],
            }

            def remote(uri, mode):
                self.assertEqual(uri, "remote/parent/workspace/task/tests/test.sh")
                return io.BytesIO(b"grader")

            prepared, manifest = prepare(remote, root, descriptor)
            self.assertEqual(len(manifest), 2)
            with zipfile.ZipFile(prepared) as archive:
                self.assertEqual(archive.read("task/instruction.md"), b"unchanged")
                self.assertEqual(archive.read("task/tests/test.sh"), b"grader")
                self.assertNotIn("task/removed.txt", archive.namelist())
                self.assertEqual(archive.read("previous-run/result.json"), b"latest result")
                self.assertEqual(
                    archive.read(f"worker-history/{sha(old_receipt)}/result.json"),
                    b"previous result",
                )
                receipt = json.loads(archive.read("previous-run/handoff.json"))
                self.assertTrue(receipt["candidate_restored_exactly"])

    def test_corrupt_parent_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = inputs(root, {"seed.txt": b"source"})
            record = parent_record(root, b"recorded result")
            (root / "parent-records/result.json").write_bytes(b"changed")
            descriptor = {
                "artifact_prefix": "remote/parent",
                "input_zip_sha256": sha(raw),
                "generated_manifest": [],
                "deleted_inputs": [],
                "task_manifest": [],
                "record_files": [record],
            }
            with self.assertRaisesRegex(ValueError, "Parent record checksum"):
                prepare(lambda *_: self.fail("Unexpected remote read"), root, descriptor)
            self.assertFalse((root / "prepared-inputs.zip").exists())

    def test_candidate_manifest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = inputs(root, {"task/instruction.md": b"unexpected"})
            descriptor = {
                "artifact_prefix": "remote/parent",
                "input_zip_sha256": sha(raw),
                "generated_manifest": [],
                "deleted_inputs": [],
                "task_manifest": [entry("instruction.md", b"expected")],
                "record_files": [],
            }
            with self.assertRaisesRegex(ValueError, "differs from final parent manifest"):
                prepare(lambda *_: self.fail("Unexpected remote read"), root, descriptor)


if __name__ == "__main__":
    unittest.main()
