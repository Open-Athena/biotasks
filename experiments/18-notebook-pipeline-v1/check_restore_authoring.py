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
