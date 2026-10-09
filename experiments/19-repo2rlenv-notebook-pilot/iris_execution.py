"""Execution adapter for an already allocated Iris host and Harbor Daytona.

This module never provisions Iris, changes inference services, or generates tasks.
The launcher must supply its own job identity and finite deadline. Task code is
executed by the pinned upstream Harbor runner in Daytona, never on this host.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


class AttachedHost:
    def __init__(self, worker_id: str):
        if not worker_id or os.environ.get("BIOTASKS_IRIS_WORKER_ID") != worker_id:
            raise RuntimeError("Requires the explicitly allocated Iris worker")
        self.id = worker_id

    def exec(self, argv, *, timeout=600, env=None):
        from repo2rlenv.execution.base import CommandResult

        if not argv or timeout <= 0:
            raise ValueError("A command and finite timeout are required")
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **(env or {})},
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        return CommandResult(
            process.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
        )

    @staticmethod
    def _remote(path: str) -> Path:
        resolved = Path(path).resolve()
        if not any(resolved.is_relative_to(root) for root in (Path("/work"), Path("/evidence"))):
            raise ValueError("Transfer path is outside the owned execution directories")
        return resolved

    def upload(self, local: Path, remote: str):
        if not local.is_file() or local.is_symlink():
            raise ValueError("Upload requires a regular file")
        target = self._remote(remote)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, target)

    def download(self, remote: str, local: Path):
        source = self._remote(remote)
        if not source.is_file():
            raise ValueError("Download requires a regular file")
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, local)


class IrisDaytonaExecution:
    def __init__(
        self,
        *,
        worker_id: str,
        deadline: datetime,
        records: Path,
        max_trials: int,
        max_solver_attempts: int,
        solver_endpoints: tuple[str, str] | None = None,
    ):
        self.worker = AttachedHost(worker_id)
        if deadline.tzinfo is None or deadline <= datetime.now(UTC):
            raise ValueError("A future timezone-aware deadline is required")
        if max_trials < 1 or not 1 <= max_solver_attempts <= 2:
            raise ValueError("Explicit trial bounds are required; at most two solves")
        self.deadline = deadline
        self.records = records
        self.max_trials = max_trials
        self.max_solver_attempts = max_solver_attempts
        self.solver_endpoints = solver_endpoints

    def identity(self):
        return dict(
            adapter="iris-daytona-v1",
            worker_id=self.worker.id,
            deadline=self.deadline.isoformat(),
            max_trials=self.max_trials,
            max_solver_attempts=self.max_solver_attempts,
            solver_route_sha256=hashlib.sha256(
                json.dumps(self.solver_endpoints).encode()
            ).hexdigest(),
            adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )

    def prepare(self, execution, ledger, run):
        from repo2rlenv.execution.artifacts import check_runtime_wheel

        check_runtime_wheel(execution.runtime_wheel)
        if not os.environ.get("DAYTONA_API_KEY"):
            raise RuntimeError("Daytona host credentials are required")
        deadline = min(self.deadline, datetime.now(UTC) + timedelta(seconds=execution.timeout_sec))
        return self.worker, sys.executable, deadline

    def run_trial(self, worker, task, output, *, trial_id, agent="nop", **kwargs):
        from repo2rlenv.execution.harbor import run_trial

        if worker.id != self.worker.id:
            raise ValueError("Execution worker identity mismatch")
        remaining = (self.deadline - datetime.now(UTC)).total_seconds()
        timeout = kwargs.get("timeout_sec", 900)
        if remaining < timeout + 120:
            raise TimeoutError("Insufficient allocation time for trial and cleanup")
        # Every attempted dispatch consumes a slot, including uncertain outcomes.
        # Re-observing the same upstream receipt does not authorize another launch.
        self.records.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(trial_id.encode()).hexdigest()
        claim = self.records / (key + ".json")
        if claim.exists():
            raise FileExistsError("Trial already claimed; reconcile its existing upstream receipt")
        previous = [json.loads(p.read_text()) for p in self.records.glob("*.json")]
        solving = agent not in {"nop", "oracle", "probe"}
        if len(previous) >= self.max_trials:
            raise RuntimeError("Total trial allowance exhausted")
        if solving and sum(row["solving"] for row in previous) >= self.max_solver_attempts:
            raise RuntimeError("Solver attempt allowance exhausted")
        if solving and kwargs.get("model") is not None:
            if self.solver_endpoints is None:
                raise ValueError("Solver requests require per-attempt gated endpoints")
            index = sum(row["solving"] for row in previous)
            kwargs["model"] = kwargs["model"].model_copy(
                update={"endpoint": self.solver_endpoints[index]}
            )
        with claim.open("x") as stream:
            json.dump(dict(trial_id=trial_id, solving=solving, output=str(output)), stream)
        return run_trial(
            worker,
            task,
            output,
            trial_id=trial_id,
            agent=agent,
            environment="daytona",
            agent_timeout_sec=300 if solving else None,
            **kwargs,
        )

    def quality_trials(self, *, directory, budget, options):
        from repo2rlenv.quality.loop.remote import RemoteTrials

        adapter = self

        class Trials:
            def identity(self):
                return adapter.identity()

            def run(self, task, role, key):
                output = directory / "trials" / key
                if (output / "trial.json").exists():
                    return RemoteTrials._read(output, task, role)
                adapter.run_trial(
                    adapter.worker,
                    task,
                    output,
                    trial_id=f"{budget.prefix}-{key}",
                    agent={
                        "baseline": "nop",
                        "oracle": "oracle",
                        "probe": "oracle",
                        "rollout": "terminus-2",
                    }[role],
                    model=options.solver_model if role == "rollout" else None,
                    ledger=budget,
                    reservation_usd=options.solver_reservation_usd,
                    reservation_wait_sec=0,
                    max_turns=options.max_turns,
                    max_tokens=options.solver_tokens,
                    timeout_sec=options.trial_timeout_sec,
                    python=sys.executable,
                )
                return RemoteTrials._read(output, task, role)

            def close(self):
                # The launcher owns the enclosing Iris job. Harbor owns each
                # Daytona task sandbox; its cleanup must be checked in evidence.
                pass

        return Trials()
