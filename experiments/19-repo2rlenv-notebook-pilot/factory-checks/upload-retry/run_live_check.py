"""Check identical uploads against Daytona with explicit synthetic HTTP failures.

No model or biological computation runs. The shared compatibility runner owns
the existing resource/time profile and cleanup; admission must happen separately.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "daytona-session-transport/run_live_check.py"
spec = importlib.util.spec_from_file_location("upload_compatibility_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

from daytona.common.errors import DaytonaError  # noqa: E402


class InjectUploadFailure:
    """Wrap the real upstream worker; never replace successful SDK delivery."""

    def __init__(self, worker, mode):
        self.worker, self.mode = worker, mode
        self.attempts = []
        self.deliveries = 0

    def upload(self, source, target):
        digest = hashlib.sha256(Path(source).read_bytes()).hexdigest()
        first = not self.attempts
        self.attempts.append({"sha256": digest, "target": target})
        if first and self.mode == "before-delivery":
            raise DaytonaError("Synthetic 502 before SDK delivery", status_code=502)
        self.worker.upload(source, target)
        self.deliveries += 1
        if first and self.mode == "after-delivery":
            raise DaytonaError("Synthetic 502 after successful SDK delivery", status_code=502)


async def checks(remote, root):
    # Use the existing actual online/offline network controls, not readback alone.
    await remote.network(False)
    await remote.network(True)
    worker = remote.worker
    cases = []
    for mode, expected_attempts, expected_deliveries in [
        ("normal", 1, 1),
        ("before-delivery", 2, 1),
        ("after-delivery", 2, 2),
    ]:
        fixture = root / (mode + ".txt")
        data = b"Synthetic file-transfer compatibility fixture.\n"
        fixture.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        target = "/work/" + fixture.name
        wrapper = InjectUploadFailure(worker, mode)
        remote.worker = wrapper
        try:
            await remote.upload(fixture, target)
        finally:
            remote.worker = worker
        assert not remote.uncertain
        receipt = json.loads(
            (root / "uploads" / f"{remote.uploads:04d}" / "upload.json").read_text()
        )
        assert receipt["state"] == "uploaded" and receipt["sha256"] == digest
        assert len(receipt["attempts"]) == len(wrapper.attempts) == expected_attempts
        assert wrapper.deliveries == expected_deliveries
        assert all(a == {"sha256": digest, "target": target} for a in wrapper.attempts)
        if expected_attempts == 2:
            assert receipt["attempts"][0]["http_status"] == 502
            assert receipt["attempts"][0]["retry_eligible"] is True
        downloaded = root / "downloaded" / fixture.name
        await remote.download(target, downloaded)
        assert downloaded.read_bytes() == data
        cases.append(
            {
                "name": mode,
                "passed": True,
                "network_policy_controls_verified": True,
                "synthetic_inputs": True,
                "failure_injected": mode != "normal",
                "natural_provider_502_reproduced": False,
                "attempts": expected_attempts,
                "successful_sdk_deliveries": expected_deliveries,
                "identical_bytes_and_target_verified": True,
                "remote_readback_sha256": digest,
                "model_or_scientific_calls": 0,
            }
        )
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
        )
    )
