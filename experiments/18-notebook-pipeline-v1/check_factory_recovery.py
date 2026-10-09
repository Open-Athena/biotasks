"""Check recovery integrity and explicit omissions without remote access."""

import hashlib
import json
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("fsspec", types.ModuleType("fsspec"))
from recover_factory_text import collect


class RecoveryChecks(unittest.TestCase):
    def test_trace_exclusion_does_not_read_verbose_artifacts(self):
        def read(uri, maximum):
            if uri.endswith("pipeline-summary.json"):
                return json.dumps({"seed": "sample", "status": "failed",
                                   "stages": [{"slot": "construction"}]}).encode()
            if uri.endswith(("zcode-events.jsonl", "launcher.log")):
                self.fail("Excluded trace was read")
            raise FileNotFoundError(uri)

        result = collect([{"seed": "sample", "prefix": "sample"}], read,
                         include_traces=False)
        self.assertIn("sample/pipeline-summary.json", result)
        omitted = json.loads(result["recovery.json"])["omissions"]
        self.assertEqual(sum(x["reason"] == "trace_excluded_by_plan" for x in omitted), 2)

    def test_verbose_first_trace_does_not_starve_later_seed_summary(self):
        files = {}
        for seed in ("first", "second"):
            files[seed + "/pipeline-summary.json"] = json.dumps({"seed": seed,
                "status": "rejected", "stages": [{"slot": "specification"}]}).encode()
            files[seed + "/specification/records/zcode-events.jsonl"] = b"x" * 850

        def read(uri, maximum):
            if uri not in files:
                raise FileNotFoundError(uri)
            return files[uri][:maximum]

        with patch("recover_factory_text.MAX_TOTAL", 1000):
            result = collect([{"seed": seed, "prefix": seed} for seed in ("first", "second")], read)
        self.assertIn("first/pipeline-summary.json", result)
        self.assertIn("second/pipeline-summary.json", result)
        self.assertNotIn("first/specification/records/zcode-events.jsonl", result)

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
