"""Execute the pinned native mutation worker, preserving evidence before cleanup.

This performs bootstrap and mutation contrasts only. It neither authors issues
nor exports/accepts Harbor tasks and makes no model requests.
"""

import argparse
import hashlib
import signal
from pathlib import Path

from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import (
    prepare_docker,
    provision_worker,
    save_record,
    stop_worker,
)

SOURCE_SHA256 = "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"


def deadline(signum, frame):
    raise TimeoutError("Mutation worker deadline reached")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--recipe", choices=("swe_smith", "swe_flow", "r2e", "r2e_gym"), default="swe_smith")
    parser.add_argument("--flow-test-paths", action="store_true")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("swe-smith-skbio-worker.json"),
    )
    parser.add_argument("--timeout-sec", type=int, default=7200)
    args = parser.parse_args()
    if not 1 <= args.timeout_sec <= 7200:
        parser.error("--timeout-sec must be between 1 and 7200")
    if args.flow_test_paths and args.recipe != "swe_flow":
        parser.error("--flow-test-paths requires --recipe swe_flow")
    if hashlib.sha256(args.source_archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected generator source archive")
    args.campaign.mkdir(parents=True, exist_ok=False)
    ledger = BudgetLedger(args.campaign / "budget.sqlite", limit_usd="5")
    spec = WorkerSpec(
        provider="daytona",
        cpus=2,
        memory_mb=4096,
        disk_gb=10,
        timeout_sec=args.timeout_sec,
        name=args.worker_name,
    )
    record = {
        "stage": "native_repository_contrasts",
        "recipe": args.recipe,
        "model_calls": 0,
        "status": "starting",
        "execution_timeout_sec": args.timeout_sec,
    }
    record["config_sha256"] = hashlib.sha256(args.config.read_bytes()).hexdigest()
    if args.recipe == "r2e":
        record["stage"] = "native_function_candidate_preparation"
    entrypoint = f"-m repo2rlenv.pipelines.recipes.{args.recipe}.worker"
    if args.recipe == "r2e_gym":
        adaptation = Path(__file__).with_name("history_contrast_batch.py")
        if not adaptation.is_file():
            adaptation = Path(__file__).parent / "continuation-20261018/history_contrast_batch.py"
        record["adaptation_sha256"] = hashlib.sha256(adaptation.read_bytes()).hexdigest()
        record["stage"] = "bounded_native_history_contrasts"
        entrypoint = "/work/native/history_contrast_batch.py"
    if args.flow_test_paths:
        adaptation = Path(__file__).with_name("swe_flow_test_paths.py")
        record["adaptation_sha256"] = hashlib.sha256(adaptation.read_bytes()).hexdigest()
        record["stage"] = "adapted_repository_contrasts"
        entrypoint = "/work/native/swe_flow_test_paths.py"
    worker = None
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, deadline)
    signal.alarm(args.timeout_sec)
    try:
        worker, receipt = provision_worker(spec, args.campaign / "workers", ledger, reserve_usd="5")
        prepare_docker(worker)
        worker.exec(["mkdir", "-p", "/work/native", "/evidence/native"], timeout=30).checked(
            "mkdir"
        )
        worker.upload(args.source_archive, "/work/native/source.tar.gz")
        worker.upload(args.config, "/work/native/config.json")
        if args.recipe == "r2e_gym":
            worker.upload(adaptation, "/work/native/history_contrast_batch.py")
        if args.flow_test_paths:
            worker.upload(adaptation, "/work/native/swe_flow_test_paths.py")
        setup = worker.exec(
            [
                "sh",
                "-c",
                (
                    "set -eu; cd /work/native; tar -xzf source.tar.gz; "
                    "uv sync --frozen --no-dev --extra mutation --extra harbor --python 3.12.3 --project huggingface-Repo2RLEnv-27d04ee "
                    ">/evidence/native/setup.log 2>&1"
                ),
            ],
            timeout=600,
        )
        record["setup_returncode"] = setup.returncode
        setup.checked("locked runtime install")
        result = worker.exec(
            [
                "sh",
                "-c",
                (
                    "export REPO2RLENV_REMOTE_WORKER=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "
                    "MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 RAYON_NUM_THREADS=1 POLARS_MAX_THREADS=1; "
                    "/work/native/huggingface-Repo2RLEnv-27d04ee/.venv/bin/python "
                    f"{entrypoint} "
                    "/work/native/config.json /evidence/native/generation "
                    ">/evidence/native/worker.log 2>&1; code=$?; "
                    "printf '%s\\n' \"$code\" >/evidence/native/worker-exit.txt; exit $code"
                ),
            ],
            timeout=min(6000, args.timeout_sec),
        )
        marker = worker.exec(["cat", "/evidence/native/worker-exit.txt"], timeout=30)
        marker.checked("read explicit mutation worker exit marker")
        native_exit = int(marker.stdout.strip())
        record.update(
            transport_reported_returncode=result.returncode,
            worker_returncode=native_exit,
            status="worker_completed" if native_exit == 0 else "worker_failed",
        )
        if native_exit != 0:
            raise RuntimeError("Native mutation worker failed; preserve original evidence")
    except BaseException as exc:
        record.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        save_record(args.campaign / "result.json", record)
        if worker is not None:
            try:
                packed = worker.exec(
                    [
                        "sh",
                        "-c",
                        "tar -czf /work/native-evidence.tar.gz -C /evidence native && stat -c %s /work/native-evidence.tar.gz",
                    ],
                    timeout=120,
                )
                packed.checked("preserve partial worker evidence")
                size = int(packed.stdout.strip())
                if size > 200 * 1024 * 1024:
                    raise ValueError("Evidence exceeds bounded local download allowance")
                worker.download(
                    "/work/native-evidence.tar.gz", args.campaign / "native-evidence.tar.gz"
                )
                record["evidence_bytes"] = size
            finally:
                record["cleanup"] = stop_worker(receipt, ledger)["state"]
                save_record(args.campaign / "result.json", record)


if __name__ == "__main__":
    main()
