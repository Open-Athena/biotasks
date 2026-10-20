"""Keep native source acquisition online and repository test execution offline."""

import re
import subprocess


def isolated_native_fetch(fetch, allowed_bases, record, *, network=None):
    allowed = frozenset(allowed_bases)
    if not allowed or any(re.fullmatch(r"[a-f0-9]{40}", value) is None for value in allowed):
        raise ValueError("Frozen full source revisions required")

    if network is None:
        def network(action, identifier):
            subprocess.run(["docker", "network", action, "bridge", identifier],
                           check=True, capture_output=True, timeout=30)

    def run(sandbox, base_commit, **kwargs):
        if base_commit not in allowed:
            raise ValueError("Source acquisition outside frozen input collection")
        identifier = sandbox.container_id
        network("connect", identifier)
        try:
            record({"stage": "native_source_fetch_network_connected", "base_commit": base_commit})
            # The native helper ensures Git and fetches its original pinned
            # commit. No repository test or source-repair command is added.
            return fetch(sandbox, base_commit, **kwargs)
        finally:
            network("disconnect", identifier)
            record({"stage": "native_source_fetch_network_disconnected_before_tests", "base_commit": base_commit})

    return run
