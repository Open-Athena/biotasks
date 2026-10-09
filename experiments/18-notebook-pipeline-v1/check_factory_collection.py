"""Offline checks for collecting multiple stages without overwriting evidence."""

import tempfile
import unittest
from pathlib import Path

from collect_factory_batch import observation_directory


class CollectionChecks(unittest.TestCase):
    def test_reviews_and_batches_get_distinct_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = observation_directory(root, "unseen", "a" * 64 + ":unseen:review")
            (first / "evidence.txt").write_text("original")
            second = observation_directory(root, "unseen", "a" * 64 + ":unseen:review_after_repair")
            third = observation_directory(root, "unseen", "b" * 64 + ":unseen:review")
            self.assertEqual(len({first, second, third}), 3)
            self.assertEqual((first / "evidence.txt").read_text(), "original")
            with self.assertRaises(FileExistsError):
                observation_directory(root, "unseen", "a" * 64 + ":unseen:review")

    def test_mismatched_seed_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            observation_directory(Path(tmp), "other", "a" * 64 + ":unseen:review")


if __name__ == "__main__":
    unittest.main()
