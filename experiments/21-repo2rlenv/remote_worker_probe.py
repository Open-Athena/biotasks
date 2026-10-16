"""One explicitly budgeted remote backend probe; no models or biological code.

Run only after approving remote CPU spend. Provider credentials must already be
in the protected process environment. Raw provider evidence stays outside Git.
"""

import argparse
import signal
from pathlib import Path

from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.execution.probes import probe_worker


def deadline(signum, frame):
    raise TimeoutError("Backend probe execution deadline reached")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--approved-budget-usd", required=True)
    args = parser.parse_args()
    args.campaign.mkdir(parents=True, exist_ok=False)
    ledger = BudgetLedger(args.campaign / "budget.sqlite", limit_usd=args.approved_budget_usd)
    spec = WorkerSpec(
        provider="daytona",
        cpus=2,
        memory_mb=4096,
        disk_gb=10,
        timeout_sec=1800,
        name=args.worker_name,
    )
    receipt = args.campaign / "workers" / f"{spec.name}.json"
    signal.signal(signal.SIGTERM, deadline)
    signal.signal(signal.SIGINT, deadline)
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    record = {"stage": "backend_preflight", "model_calls": 0, "biological_execution": False}
    created = False
    try:
        worker, receipt = provision_worker(spec, args.campaign / "workers", ledger, reserve_usd="5")
        created = True
        record["probe"] = probe_worker(worker, args.campaign / "probe")
        record["status"] = "probe_completed"
    except BaseException as exc:
        record["status"] = "probe_failed"
        record["error_type"] = type(exc).__name__
        record["creation_reconciliation_required"] = not created and receipt.exists()
        raise
    finally:
        signal.alarm(0)
        save_record(args.campaign / "result.json", record)
        if created:
            # Native stop records uncertain deletion rather than hiding it.
            record["cleanup"] = stop_worker(receipt, ledger)["state"]
            save_record(args.campaign / "result.json", record)


if __name__ == "__main__":
    main()
