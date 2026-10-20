"""Check that repository tests cannot start with source-fetch networking active."""

import unittest
from types import SimpleNamespace

from source_fetch_isolation import isolated_native_fetch


class SourceFetchIsolationTests(unittest.TestCase):
    def exercise(self, fail=False):
        base = "a" * 40
        state = {"network": False, "fetches": 0}
        events = []

        def network(action, identifier):
            self.assertEqual(identifier, "owned-synthetic-container")
            self.assertEqual(state["network"], action == "disconnect")
            state["network"] = action == "connect"

        def fetch(sandbox, revision, *, timeout):
            self.assertTrue(state["network"])
            self.assertEqual(revision, base)
            self.assertEqual(timeout, 600)
            state["fetches"] += 1
            if fail:
                raise RuntimeError("synthetic source-fetch failure")
            return True

        wrapped = isolated_native_fetch(fetch, [base], events.append, network=network)
        sandbox = SimpleNamespace(container_id="owned-synthetic-container")
        if fail:
            with self.assertRaises(RuntimeError):
                wrapped(sandbox, base, timeout=600)
        else:
            self.assertTrue(wrapped(sandbox, base, timeout=600))
        self.assertFalse(state["network"])
        self.assertEqual(state["fetches"], 1)
        self.assertEqual(events[-1]["stage"], "native_source_fetch_network_disconnected_before_tests")
        with self.assertRaises(ValueError):
            wrapped(sandbox, "b" * 40, timeout=600)
        self.assertFalse(state["network"])
        self.assertEqual(state["fetches"], 1)

    def test_success_returns_to_offline_execution(self):
        self.exercise()

    def test_failed_fetch_returns_to_offline_execution(self):
        self.exercise(fail=True)


if __name__ == "__main__":
    unittest.main()
