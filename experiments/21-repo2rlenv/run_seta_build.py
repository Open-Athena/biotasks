"""Bounded Iris controller for native SETA materialization on one Daytona worker."""

import argparse
import json
import os
import signal
import sys
from pathlib import Path

import build_seta_designs
from preserve_author_output import preserve
from replay_seta_designs import saved_designer
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.artifacts import check_runtime_wheel
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.spec.input import GenerationInput


def deadline(signum, frame):
    raise TimeoutError("SETA controller execution deadline")


def verify_deleted(worker):
    try:
        worker.client.get(worker.id)
    except Exception as exc:
        code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return {"independently_confirmed": code == 404, "http_status": code,
                "error_type": type(exc).__name__}
    return {"independently_confirmed": False, "state": "still_present"}


def recover_remote(worker, campaign):
    """Preserve remaining trial logs before cleanup, including interrupted trials."""
    script = """import os,tarfile
from pathlib import Path
files=[];total=0
for root in (Path('/evidence'),Path('/work/trials')):
 for directory, dirs, names in os.walk(root,followlinks=False):
  for name in names:
   p=Path(directory)/name
   if p.is_symlink() or not p.is_file():continue
   total+=p.stat().st_size
   if total>64*1024**2:raise RuntimeError('Remote evidence exceeds capture bound')
   files.append(p)
with tarfile.open('/work/seta-remote-evidence.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p).lstrip('/'),recursive=False)
"""
    worker.exec(["/opt/repo2rlenv/bin/python", "-c", script], timeout=90).checked("Evidence capture")
    worker.download("/work/seta-remote-evidence.tar.gz", campaign / "remote-evidence.tar.gz")


def run(args):
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1":
        raise RuntimeError("Approved remote model controller required")
    capture = Path(os.environ["IRIS_OUTPUT_DIR"]).resolve()
    wheel_hash = check_runtime_wheel(args.wheel)
    # Fail before allocation if saved designs or any seed changed.
    designer = saved_designer(args.designs, args.designs_sha256)
    seeds = json.loads(args.seeds.read_text())
    if len(seeds) != 3:
        raise ValueError("Expected the declared three-seed cohort")
    args.campaign.mkdir(parents=True, exist_ok=False)
    for seed in seeds:
        designer(seed, model=None, ledger=None, receipt=args.campaign / "preflight" / (seed["id"] + ".json"),
                 operation_id="preflight", resume=False)
    ledger = BudgetLedger(args.campaign / "budget.sqlite3", limit_usd="20")
    worker = None
    receipt = None
    state = {"stage": "native_build_from_saved_designs", "status": "starting",
             "runtime_wheel_sha256": wheel_hash, "independently_validated_tasks": 0}
    old_argv = sys.argv
    old_capture = os.environ["IRIS_OUTPUT_DIR"]
    try:
        worker, receipt = provision_worker(
            WorkerSpec(provider="daytona", cpus=2, memory_mb=4096, disk_gb=10,
                       timeout_sec=7200, name=args.worker_name),
            args.campaign / "workers", ledger, reserve_usd="5",
        )
        spec = GenerationInput.model_validate({
            "source": {"kind": "seeds", "path": str(args.seeds.resolve())},
            "pipeline": {"name": "terminal_synth", "recipe": "seta_seed2synth"},
            "llm": {"provider": "openai", "model": "glm-5.3",
                    "endpoint": os.environ["BIOTASKS21_GLM_ENDPOINT"],
                    "api_key_env": "BIOTASKS21_GLM_KEY", "max_concurrent": 1,
                    "timeout_sec": 1200, "fallback": None},
            "execution": {"worker_receipt": str(receipt.resolve()),
                          "runtime_wheel": str(args.wheel.resolve()),
                          "campaign_dir": str(args.campaign.resolve()),
                          "run_id": "seta-build-01", "timeout_sec": 6600, "resume": False},
            "output": {"destination": str((args.campaign / "tasks").resolve()),
                       "org": "open-athena", "dataset_name": "biotasks21-seta"},
            "auth": {"use_gh_cli": False},
        })
        input_path = args.campaign / "input-private.json"
        save_record(input_path, spec.model_dump(mode="json"))
        os.environ["IRIS_OUTPUT_DIR"] = str(capture / "before-cleanup")
        sys.argv = ["build_seta_designs", "--input", str(input_path), "--designs", str(args.designs),
                    "--designs-sha256", args.designs_sha256, "--adaptation", str(args.adaptation)]
        build_seta_designs.main()
        state["status"] = "completed"
    except BaseException as exc:
        state.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        sys.argv = old_argv
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
                    stop_worker(receipt, ledger)
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
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--designs", type=Path, required=True)
    parser.add_argument("--designs-sha256", required=True)
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
