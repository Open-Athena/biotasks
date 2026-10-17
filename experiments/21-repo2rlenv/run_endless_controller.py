"""Bounded Iris controller for native Endless Terminals biological generation on one Daytona worker."""

import argparse
import json
import os
import signal
import time
from pathlib import Path
from types import SimpleNamespace

import build_endless_biological
from preserve_author_output import preserve
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.artifacts import check_runtime_wheel
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.spec.input import GenerationInput


def deadline(signum, frame):
    raise TimeoutError("Endless Terminals controller execution deadline")


def verify_deleted(worker, timeout=120):
    deadline_at = time.monotonic() + timeout
    while True:
        try:
            worker.client.get(worker.id)
        except Exception as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if code == 404:
                return {"independently_confirmed": True, "http_status": 404}
            return {"independently_confirmed": False, "http_status": code,
                    "error_type": type(exc).__name__}
        if time.monotonic() >= deadline_at:
            return {"independently_confirmed": False, "state": "still_present"}
        time.sleep(min(5, deadline_at - time.monotonic()))


def recover_remote(worker, campaign):
    """Preserve remaining trial logs before cleanup, including interrupted trials."""
    script = """import os,tarfile
from pathlib import Path
from types import SimpleNamespace
files=[];total=0
for root in (Path('/evidence'),Path('/work/trials')):
 for directory, dirs, names in os.walk(root,followlinks=False):
  for name in names:
   p=Path(directory)/name
   if p.is_symlink() or not p.is_file():continue
   total+=p.stat().st_size
   if total>64*1024**2:raise RuntimeError('Remote evidence exceeds capture bound')
   files.append(p)
with tarfile.open('/work/endless_terminals-biological-remote-evidence.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p).lstrip('/'),recursive=False)
"""
    worker.exec(["/opt/repo2rlenv/bin/python", "-c", script], timeout=90).checked("Evidence capture")
    worker.download("/work/endless_terminals-biological-remote-evidence.tar.gz", campaign / "remote-evidence.tar.gz")


def run(args):
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1":
        raise RuntimeError("Approved remote model controller required")
    capture = Path(os.environ["IRIS_OUTPUT_DIR"]).resolve()
    wheel_hash = check_runtime_wheel(args.wheel)
    settings = json.loads(args.adaptation.read_text())
    # Validate frozen sampler records and settings before worker allocation.
    spec = GenerationInput.model_validate({
        "source": {"kind": "seeds", "path": str((args.manifest.parent / "sampler.json").resolve())},
        "pipeline": {"name": "terminal_synth", "recipe": "endless_terminals"},
        "llm": {"provider": "openai", "model": "glm-5.3",
                "endpoint": os.environ["BIOTASKS21_GLM_ENDPOINT"],
                "api_key_env": "BIOTASKS21_GLM_KEY", "max_concurrent": 1,
                "timeout_sec": 1200, "fallback": None},
        "execution": {"worker_receipt": str((args.campaign / "pending-worker.json").resolve()),
                      "runtime_wheel": str(args.wheel.resolve()),
                      "campaign_dir": str(args.campaign.resolve()),
                      "run_id": "endless-terminals-biological-build-01", "timeout_sec": 6600, "resume": False},
        "output": {"destination": str((args.campaign / "tasks").resolve()),
                   "org": "open-athena", "dataset_name": "biotasks21-endless_terminals-biological"},
        "auth": {"use_gh_cli": False},
    })
    build_endless_biological.prepare(spec, args.manifest, settings)
    args.campaign.mkdir(parents=True, exist_ok=False)
    # Native dollar reservations meter free calls; these are not provider charges.
    ledger = BudgetLedger(args.campaign / "budget.sqlite3", limit_usd="50")
    worker = None
    receipt = None
    state = {"stage": "native_endless_terminals-biological_build", "status": "starting",
             "runtime_wheel_sha256": wheel_hash, "independently_validated_tasks": 0}
    old_capture = os.environ["IRIS_OUTPUT_DIR"]
    try:
        worker, receipt = provision_worker(
            WorkerSpec(provider="daytona", cpus=2, memory_mb=4096, disk_gb=10,
                       timeout_sec=7200, name=args.worker_name),
            args.campaign / "workers", ledger, reserve_usd="5",
        )
        spec.execution.worker_receipt = receipt.resolve()
        input_path = args.campaign / "input-private.json"
        save_record(input_path, spec.model_dump(mode="json"))
        os.environ["IRIS_OUTPUT_DIR"] = str(capture / "before-cleanup")
        build_endless_biological.run(SimpleNamespace(input=input_path, manifest=args.manifest,
                                          adaptation=args.adaptation))
        state["status"] = "completed"
    except BaseException as exc:
        state.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        os.environ["IRIS_OUTPUT_DIR"] = old_capture
        try:
            if receipt is not None:
                try:
                    recover_remote(worker, args.campaign)
                    state["remote_evidence_recovered"] = True
                except Exception as exc:
                    state["remote_evidence_recovered"] = False
                    state["remote_evidence_error_type"] = type(exc).__name__
                finally:
                    try:
                        stop_worker(receipt, ledger)
                    except Exception as exc:
                        state["stop_error_type"] = type(exc).__name__
                    state["cleanup"] = verify_deleted(worker)
        except BaseException as exc:
            state["cleanup"] = {"independently_confirmed": False, "error_type": type(exc).__name__}
        finally:
            save_record(args.campaign / "controller-result.json", state)
            preserve(args.campaign, capture / "after-cleanup")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    args = parser.parse_args()
    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, deadline)
    timeout = int(os.environ.get("BIOTASKS21_CONTROLLER_DEADLINE", "6900"))
    if not 60 <= timeout <= 6900:
        raise ValueError("Controller deadline must leave time for cleanup")
    signal.alarm(timeout)
    run(args)


if __name__ == "__main__":
    main()
