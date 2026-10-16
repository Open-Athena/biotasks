"""Export native SWE-smith tasks and run deterministic Harbor controls remotely.

Preserve complete task bundles and control evidence before worker deletion.
No model calls or blind solving occur here.
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
    raise TimeoutError("Native control worker deadline reached")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=(
            "smith-controls",
            "flow-controls",
            "flow-independent",
            "biopython-cve",
            "biopython-commit",
            "marin-schema",
            "marin-runtime",
        ),
        default="smith-controls",
    )
    parser.add_argument("--generation-archive", type=Path)
    parser.add_argument("--issues", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    if args.stage in ("smith-controls", "flow-controls") and (
        args.generation_archive is None or args.issues is None
    ):
        parser.error("Repository controls require --generation-archive and --issues")
    if args.stage == "flow-controls" and args.config is None:
        parser.error("Flow controls require --config")
    if args.stage == "flow-independent" and args.generation_archive is None:
        parser.error("Independent controls require the original control archive")
    if hashlib.sha256(args.source_archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected generator source archive")
    args.campaign.mkdir(parents=True, exist_ok=False)
    ledger = BudgetLedger(args.campaign / "budget.sqlite", limit_usd="5")
    spec = WorkerSpec(
        provider="daytona",
        cpus=2,
        memory_mb=4096,
        disk_gb=10,
        timeout_sec=7200,
        name=args.worker_name,
    )
    record = {"stage": args.stage, "model_calls": 0, "status": "starting"}
    worker = None
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, deadline)
    signal.alarm(7200)
    try:
        worker, receipt = provision_worker(spec, args.campaign / "workers", ledger, reserve_usd="5")
        prepare_docker(worker)
        worker.exec(["mkdir", "-p", "/work/native", "/evidence/native"], timeout=30).checked(
            "mkdir"
        )
        worker.upload(args.source_archive, "/work/native/source.tar.gz")
        root = Path(__file__).parent
        if args.stage in ("smith-controls", "flow-controls"):
            worker.upload(args.generation_archive, "/work/native/generation.tar.gz")
            worker.upload(args.issues, "/work/native/issues.json")
            worker.upload(root / "export_verify_smith.py", "/work/native/export_verify_smith.py")
            worker.upload(
                args.config or root / "swe-smith-skbio-worker.json", "/work/native/config.json"
            )
            unpack = "mkdir inputs; tar -xzf generation.tar.gz -C inputs; "
            entry = (
                "/work/native/export_verify_smith.py "
                "--generation /work/native/inputs/native/generation "
                "--issues /work/native/issues.json --config /work/native/config.json "
                "--output /evidence/native/validation "
            )
            if args.stage == "flow-controls":
                entry += "--recipe swe_flow "
        elif args.stage == "flow-independent":
            worker.upload(args.generation_archive, "/work/native/controls.tar.gz")
            for script in ("prepare_flow_independent_controls.py", "run_flow_independent.py"):
                worker.upload(root / script, "/work/native/" + script)
            unpack = "mkdir inputs; tar -xzf controls.tar.gz -C inputs; "
            entry = "/work/native/run_flow_independent.py "
        elif args.stage == "biopython-commit":
            worker.upload(
                root / "replay_biopython_commit.py", "/work/native/replay_biopython_commit.py"
            )
            worker.upload(root / "biopython-cve.Dockerfile", "/work/native/Dockerfile")
            unpack = ""
            entry = "/work/native/replay_biopython_commit.py "
        elif args.stage == "biopython-cve":
            for source, target in (
                ("replay_biopython_cve.py", "replay_biopython_cve.py"),
                ("biopython-cve.Dockerfile", "Dockerfile"),
                ("evidence/osv-intake/biopython.json", "advisories.json"),
                ("evidence/osv-intake/biopython-fix.diff", "fix.diff"),
            ):
                worker.upload(root / source, "/work/native/" + target)
            unpack = ""
            entry = "/work/native/replay_biopython_cve.py "
        else:
            worker.upload(
                root / "validate_marin_preparation.py", "/work/native/validate_marin_preparation.py"
            )
            worker.upload(
                root / "evidence/marin-pr2630-preparation/task.json", "/work/native/task.json"
            )
            unpack = ""
            entry = "/work/native/validate_marin_preparation.py "
            if args.stage == "marin-runtime":
                worker.upload(
                    root / "check_marin_runtime.py", "/work/native/check_marin_runtime.py"
                )
                entry += "--runtime "
        setup = worker.exec(
            [
                "sh",
                "-c",
                (
                    "set -eu; cd /work/native; tar -xzf source.tar.gz; "
                    + unpack
                    + "uv sync --frozen --no-dev --extra mutation --extra harbor --python 3.12.3 --project huggingface-Repo2RLEnv-27d04ee "
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
                    + entry
                    + ">/evidence/native/worker.log 2>&1; code=$?; "
                    "printf '%s\\n' \"$code\" >/evidence/native/worker-exit.txt; exit $code"
                ),
            ],
            timeout=6000,
        )
        record.update(
            worker_returncode=result.returncode,
            status="worker_completed" if result.returncode == 0 else "worker_failed",
        )
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
