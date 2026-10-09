"""Check recovery integrity and explicit omissions without remote access."""

import hashlib
import json
import sys
import types
import unittest

sys.modules.setdefault("fsspec", types.ModuleType("fsspec"))
from recover_factory_text import collect


class RecoveryChecks(unittest.TestCase):
    def fixture(self, corrupt=False, unsafe=False):
        value = b'{"status": "rejected", "rationale": "fixture"}'
        path = "../escape.json" if unsafe else "proposal.json"
        files = {
            "test/pipeline-summary.json": json.dumps({"seed": "unseen", "status": "rejected",
                "stages": [{"slot": "specification"}]}).encode(),
            "test/specification/records/artifact-manifest.json": json.dumps([
                {"path": path, "size": len(value), "sha256": hashlib.sha256(value).hexdigest()},
                {"path": "input.h5ad", "size": 10, "sha256": "a" * 64},
            ]).encode(),
            "test/specification/workspace/" + path: b"corrupt" if corrupt else value,
        }

        def read(uri, maximum):
            if uri not in files:
                raise FileNotFoundError(uri)
            return files[uri][:maximum]

        return collect([{"seed": "unseen", "prefix": "test"}], read)

    def test_preserves_rejection_and_records_missing_and_binary_evidence(self):
        result = self.fixture()
        self.assertIn("unseen/specification/workspace/proposal.json", result)
        receipt = json.loads(result["recovery.json"])
        self.assertFalse(receipt["complete_binary_artifact_recovery"])
        self.assertEqual({item["reason"] for item in receipt["omissions"]},
                         {"not_available", "outside_text_selection"})
        self.assertTrue(any(item["source_manifest_verified"] for item in receipt["files"]))

    def test_corruption_fails_instead_of_becoming_recovered_evidence(self):
        with self.assertRaisesRegex(ValueError, "source manifest"):
            self.fixture(corrupt=True)

    def test_manifest_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe evidence path"):
            self.fixture(unsafe=True)


if __name__ == "__main__":
    unittest.main()
