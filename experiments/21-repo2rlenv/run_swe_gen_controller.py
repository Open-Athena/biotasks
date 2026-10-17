"""Bounded Iris controller for native history recipes on one Daytona worker."""

import argparse
import json
import os
import signal
import time
from pathlib import Path
from types import SimpleNamespace

import run_swe_gen_recipe
from preserve_author_output import preserve
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.artifacts import check_runtime_wheel
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.spec.input import GenerationInput


def deadline(signum, frame):
    raise TimeoutError("History controller execution deadline")


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
with tarfile.open('/work/history-remote-evidence.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p).lstrip('/'),recursive=False)
"""
    worker.exec(["/opt/repo2rlenv/bin/python", "-c", script], timeout=90).checked("Evidence capture")
    worker.download("/work/history-remote-evidence.tar.gz", campaign / "remote-evidence.tar.gz")


def run(args):
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1":
        raise RuntimeError("Approved remote model controller required")
    capture = Path(os.environ["IRIS_OUTPUT_DIR"]).resolve()
    wheel_hash = check_runtime_wheel(args.wheel)
    profile = json.loads(args.profile.read_text())
    settings = json.loads(args.adaptation.read_text())
    recipe = profile['recipe']
    run_id = profile.get('run_id', recipe.replace('_', '-') + '-skbio-01')
    spec = GenerationInput.model_validate({
        "source": profile['source'],
        "pipeline": {"name": "pr_to_env", "recipe": recipe},
        "llm": {"provider": "openai", "model": "glm-5.3",
                "endpoint": os.environ["BIOTASKS21_GLM_ENDPOINT"],
                "api_key_env": "BIOTASKS21_GLM_KEY", "max_concurrent": 1,
                "timeout_sec": 1200, "fallback": None},
        "execution": {"worker_receipt": str((args.campaign / "pending-worker.json").resolve()),
                      "runtime_wheel": str(args.wheel.resolve()),
                      "campaign_dir": str(args.campaign.resolve()),
                      "run_id": run_id, "timeout_sec": 6600, "resume": False},
        "output": {"destination": str((args.campaign / "tasks").resolve()),
                   "org": "open-athena", "dataset_name": "biotasks21-history"},
        "auth": {"use_gh_cli": False},
    })
    # Native validation and frozen PR cache happen before allocation.
    # Validate in a separate temporary directory so the campaign can be created exclusively.
    import tempfile
    with tempfile.TemporaryDirectory() as preflight:
        check_spec = spec.model_copy(deep=True)
        check_spec.execution.campaign_dir = Path(preflight)
        run_swe_gen_recipe.prepare(check_spec, profile, settings, args.source, args.source_sha256)
    args.campaign.mkdir(parents=True, exist_ok=False)
    # Native dollar reservations meter free calls; these are not provider charges.
    ledger = BudgetLedger(args.campaign / "budget.sqlite3", limit_usd="50")
    worker = None
    receipt = None
    state = {"stage": "native_swe_gen_generation", "status": "starting",
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
        run_swe_gen_recipe.run(SimpleNamespace(input=input_path, profile=args.profile,
                                              adaptation=args.adaptation, source=args.source,
                                              source_sha256=args.source_sha256))
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
            preserve(args.campaign, capture / "after-cleanup", max_bytes=2*1024**3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--source-sha256")
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
