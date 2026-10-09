"""One owned network/resource preflight; no model or biological task generation."""

from __future__ import annotations

import json
import shlex
import socket
import time
from pathlib import Path

from daytona import CreateSandboxFromImageParams, Resources
from daytona.common.errors import DaytonaNotFoundError
from repo2rlenv.execution.lifecycle import save_record

# Independent public destinations; check reachability from the host first so an
# unreachable service cannot by itself count as evidence of sandbox isolation.
TARGETS = [("1.1.1.1", 443), ("example.com", 443)]
PROBE = """import json, socket
results = []
for host, port in TARGETS:
    try:
        with socket.create_connection((host, port), timeout=3):
            reachable = True
    except OSError:
        reachable = False
    results.append({'host': host, 'port': port, 'reachable': reachable})
print(json.dumps(results))
"""


def run(client, *, root: Path, campaign: str, deadline: float) -> dict:
    """A failed/uncertain creation consumes the sole preflight allowance."""
    if deadline - time.time() < 600:
        raise TimeoutError("Need ten minutes remaining for preflight and cleanup")
    root.mkdir(parents=True, exist_ok=True)
    claim = root / "infrastructure-preflight-claim.json"
    name = "biotasks19-" + campaign + "-preflight"
    with claim.open("x") as stream:
        json.dump({"name": name, "started": time.time(), "max_seconds": 600}, stream)
    record = {
        "name": name,
        "passed": False,
        "cleanup_verified": False,
        "limitations": "Representative outbound TCP probes, not exhaustive network attestation",
    }
    sandbox = None
    creation_started = False
    try:
        host_results = []
        for host, port in TARGETS:
            with socket.create_connection((host, port), timeout=5):
                host_results.append({"host": host, "port": port, "reachable": True})
        record["host_controls"] = host_results
        creation_started = True
        sandbox = client.create(
            CreateSandboxFromImageParams(
                name=name,
                image="python:3.12-slim",
                language="python",
                resources=Resources(cpu=1, memory=2, disk=10),
                labels={
                    "biotasks.issue": "19",
                    "biotasks.campaign": campaign,
                    "biotasks.role": "preflight",
                },
                network_block_all=True,
                public=False,
                auto_delete_interval=0,
                auto_stop_interval=10,
                ttl_minutes=10,
            ),
            timeout=420,
        )
        record["sandbox_id"] = sandbox.id
        save_record(root / "infrastructure-preflight.json", record)
        sandbox.refresh_data(request_timeout=15)
        resources = {key: getattr(sandbox, key) for key in ("cpu", "memory", "disk")}
        record["resources"] = resources
        record["network_block_all"] = sandbox.network_block_all
        if (
            resources != {"cpu": 1, "memory": 2, "disk": 10}
            or sandbox.network_block_all is not True
        ):
            raise RuntimeError(
                "Provider resource/network configuration differs from approved profile"
            )
        command = "python -c " + shlex.quote("TARGETS = " + repr(TARGETS) + "\n" + PROBE)
        probe = sandbox.process.exec(command, timeout=15)
        if probe.exit_code != 0:
            raise RuntimeError("Network probe did not execute successfully")
        outcomes = json.loads(probe.result)
        record["sandbox_probes"] = outcomes
        expected = [{"host": host, "port": port, "reachable": False} for host, port in TARGETS]
        if outcomes != expected:
            raise RuntimeError("Offline sandbox could reach an external destination")
        record["passed"] = True
    except BaseException as error:
        record["error_type"] = type(error).__name__
        raise
    finally:
        # Reconcile by the pre-recorded unique name if creation was uncertain.
        # A transient observation failure is not evidence that cleanup succeeded.
        try:
            if not creation_started:
                record["cleanup_verified"] = True
            elif sandbox is None:
                try:
                    sandbox = client.get(name, request_timeout=15)
                except DaytonaNotFoundError:
                    # The timed-out create may still be in flight. Preserve the
                    # uncertainty; a later observation must reconcile its TTL.
                    record["cleanup_verified"] = False
            if sandbox is not None:
                client.delete(sandbox, timeout=60, wait=True)
                try:
                    remaining = client.get(sandbox.id, request_timeout=15)
                except DaytonaNotFoundError:
                    record["cleanup_verified"] = True
                else:
                    state = getattr(remaining.state, "value", remaining.state)
                    record["cleanup_verified"] = state == "destroyed"
        finally:
            record["finished"] = time.time()
            save_record(root / "infrastructure-preflight.json", record)
    if not record["cleanup_verified"]:
        raise RuntimeError("Preflight cleanup is unverified; do not launch another sandbox")
    return record
