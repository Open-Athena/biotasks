"""Export native SWE-smith tasks and run deterministic Harbor controls remotely.

Preserve complete task bundles and control evidence before worker deletion.
No model calls or blind solving occur here.
"""

import argparse
import hashlib
import json
import os
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
            "lcc-independent",
            "history-independent",
            "qcp-independent",
            "code-instruct-validation",
            "biopython-cve",
            "biopython-commit",
            "biopython-pr",
            "skbio-pr",
            "skbio-pr-compiled",
            "skbio-pr-controls",
            "skbio-pr-controls-offline",
            "skbio-pr-controls-partial",
            "marin-schema",
            "marin-runtime",
            "marin-pr-runtime",
            "marin-lcc-runtime",
            "marin-scaler-runtime",
        ),
        default="smith-controls",
    )
    parser.add_argument("--generation-archive", type=Path)
    parser.add_argument("--issues", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--validation-repo", choices=("biopython", "scikit-bio"), default="biopython")
    args = parser.parse_args()
    if args.stage in ("smith-controls", "flow-controls", "code-instruct-validation") and (
        args.generation_archive is None or args.issues is None
    ):
        parser.error("Repository controls require --generation-archive and --issues")
    if args.stage == "flow-controls" and args.config is None:
        parser.error("Flow controls require --config")
    if args.stage in ("flow-independent", "lcc-independent") and args.generation_archive is None:
        parser.error("Independent controls require the original control archive")
    if args.stage in ("skbio-pr-controls", "skbio-pr-controls-offline", "skbio-pr-controls-partial") and args.generation_archive is None:
        parser.error("Scikit-bio PR controls require the original native task archive")
    if args.stage in ("marin-lcc-runtime", "marin-scaler-runtime") and args.generation_archive is None:
        parser.error("LCC parity requires its source-hashed input archive")
    if args.stage in ('history-independent', 'qcp-independent'):
        if args.generation_archive is None or args.config is None:
            parser.error('History controls require frozen task archive and configuration')
        history_config = json.loads(args.config.read_text())
        allowed = ('swe-gen-d929391f2255c34c2485',) if args.stage == 'qcp-independent' else ('swe-next-bf5a63ab005130388e02', 'r2e-gym-bf5a63ab005130388e02', 'swe-gen-30ce0424b0dc2d06bf6b')
        if history_config['task'] not in allowed:
            parser.error('Unknown reviewed history task')
        with args.generation_archive.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != history_config['archive_sha256']:
                parser.error('History task archive changed')
    if args.stage == "code-instruct-validation":
        authored = json.loads(args.issues.read_text())
        if authored.get("stage") != "authoring_only" or not 1 <= len(authored.get("records", [])) <= 10:
            parser.error("Expected one to ten authored candidates before allocating a worker")
    if hashlib.sha256(args.source_archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected generator source archive")
    controller_timeout = int(os.environ.get("BIOTASKS21_CONTROLLER_DEADLINE", "7200"))
    if not 60 <= controller_timeout <= 7200:
        raise ValueError("Invalid controller deadline")
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
    signal.alarm(controller_timeout)
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
        elif args.stage == "code-instruct-validation":
            worker.upload(args.generation_archive, "/work/native/controls.tar.gz")
            worker.upload(args.issues, "/work/native/candidates.json")
            for script in ("run_code_instruct_validation.py", "validate_code_instruct.py"):
                worker.upload(root / script, "/work/native/" + script)
            unpack = "mkdir inputs; tar -xzf controls.tar.gz -C inputs; "
            entry = "/work/native/run_code_instruct_validation.py --repo " + args.validation_repo + " "
        elif args.stage in ('history-independent', 'qcp-independent'):
            worker.upload(args.generation_archive, '/work/native/controls.tar.gz')
            scripts = ('prepare_skbio_pr_controls.py', 'prepare_qcp_controls.py', 'run_qcp_independent.py', 'pack_qcp_evidence.py') if args.stage == 'qcp-independent' else ('prepare_skbio_pr_controls.py', 'run_history_independent.py')
            for script in scripts:
                worker.upload(root/script, '/work/native/'+script)
            unpack = 'mkdir -p inputs; tar -xzf controls.tar.gz -C inputs; '
            runner = 'run_qcp_independent.py' if args.stage == 'qcp-independent' else 'run_history_independent.py'
            entry = '/work/native/' + runner + ' --task /work/native/inputs/native/tasks/' + history_config['task'] + ' '
        elif args.stage in ("flow-independent", "lcc-independent"):
            worker.upload(args.generation_archive, "/work/native/controls.tar.gz")
            family = "flow" if args.stage == "flow-independent" else "lcc"
            for script in (f"prepare_{family}_independent_controls.py", f"run_{family}_independent.py"):
                worker.upload(root / script, "/work/native/" + script)
            unpack = "mkdir inputs; tar -xzf controls.tar.gz -C inputs; "
            entry = f"/work/native/run_{family}_independent.py "
        elif args.stage in ("skbio-pr-controls", "skbio-pr-controls-offline", "skbio-pr-controls-partial"):
            worker.upload(args.generation_archive, "/work/native/controls.tar.gz")
            for filename in ("prepare_skbio_pr_controls.py", "run_skbio_pr_controls.py"):
                worker.upload(root / filename, "/work/native/" + filename)
            worker.upload(root / "skbio-pr-compiled.Dockerfile", "/work/native/Dockerfile")
            unpack = "mkdir inputs; tar -xzf controls.tar.gz -C inputs; "
            entry = "/work/native/run_skbio_pr_controls.py "
            if args.stage in ("skbio-pr-controls-offline", "skbio-pr-controls-partial"):
                entry += "--offline-profile "
            if args.stage == "skbio-pr-controls-partial":
                entry += "--partial-control "
        elif args.stage in ("skbio-pr", "skbio-pr-compiled"):
            worker.upload(root / "replay_skbio_pr.py", "/work/native/replay_skbio_pr.py")
            dockerfile = "skbio-pr-compiled.Dockerfile" if args.stage == "skbio-pr-compiled" else "skbio-pr.Dockerfile"
            worker.upload(root / dockerfile, "/work/native/Dockerfile")
            for filename in ("pr2633.json", "pr2633.diff", "issue2631.json"):
                worker.upload(root / "evidence/skbio-pr-runtime-intake" / filename,
                              "/work/native/" + filename)
            unpack = ""
            entry = "/work/native/replay_skbio_pr.py "
            if args.stage == "skbio-pr-compiled":
                entry += "--restore-compiled "
        elif args.stage == "biopython-pr":
            worker.upload(root / "replay_biopython_pr.py", "/work/native/replay_biopython_pr.py")
            worker.upload(root / "biopython-cve.Dockerfile", "/work/native/Dockerfile")
            for filename in ("pr5148.json", "pr5148.diff", "issue5109.json"):
                worker.upload(
                    root / "evidence/pr-runtime-intake" / filename, "/work/native/" + filename
                )
            unpack = ""
            entry = "/work/native/replay_biopython_pr.py "
        elif args.stage == "biopython-commit":
            worker.upload(
                root / "replay_biopython_commit.py", "/work/native/replay_biopython_commit.py"
            )
            worker.upload(root / "biopython-cve.Dockerfile", "/work/native/Dockerfile")
            for script in ("check_glm_solver_transport.py", "glm_solver_settings.py"):
                worker.upload(root / script, "/work/native/" + script)
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
        elif args.stage == "marin-scaler-runtime":
            for name in ("validate_marin_preparation.py", "check_marin_runtime.py", "check_marin_scaler_runtime.py"):
                worker.upload(root / name, "/work/native/" + name)
            worker.upload(args.generation_archive, "/work/native/scaler-inputs.tar.gz")
            unpack = "tar -xzf scaler-inputs.tar.gz; "
            entry = "/work/native/validate_marin_preparation.py --runtime --runtime-script check_marin_scaler_runtime.py "
        elif args.stage == "marin-lcc-runtime":
            for name in ("validate_marin_preparation.py", "check_marin_runtime.py", "check_marin_lcc_runtime.py"):
                worker.upload(root / name, "/work/native/" + name)
            worker.upload(args.generation_archive, "/work/native/lcc-inputs.tar.gz")
            unpack = "tar -xzf lcc-inputs.tar.gz; "
            entry = "/work/native/validate_marin_preparation.py --runtime --runtime-script check_marin_lcc_runtime.py "
        else:
            worker.upload(
                root / "validate_marin_preparation.py", "/work/native/validate_marin_preparation.py"
            )
            prepared = "marin-pr2633-preparation" if args.stage == "marin-pr-runtime" else "marin-pr2630-preparation"
            worker.upload(root / "evidence" / prepared / "task.json", "/work/native/task.json")
            unpack = ""
            entry = "/work/native/validate_marin_preparation.py "
            if args.stage in ("marin-runtime", "marin-pr-runtime"):
                worker.upload(
                    root / "check_marin_runtime.py", "/work/native/check_marin_runtime.py"
                )
                entry += "--runtime "
                if args.stage == "marin-pr-runtime":
                    worker.upload(root / "check_marin_pr_runtime.py", "/work/native/check_marin_pr_runtime.py")
                    worker.upload(root / "evidence/marin-pr2633-preparation/parity-controls.json", "/work/native/parity-controls.json")
                    entry += "--runtime-script check_marin_pr_runtime.py "
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
        if args.stage == "biopython-commit":
            fixture = worker.exec(
                [
                    "sh",
                    "-c",
                    "LITELLM_LOCAL_MODEL_COST_MAP=True "
                    "/work/native/huggingface-Repo2RLEnv-27d04ee/.venv/bin/python "
                    "/work/native/check_glm_solver_transport.py "
                    ">/evidence/native/solver-transport-fixture.log 2>&1",
                ],
                timeout=60,
            )
            record["solver_transport_fixture_returncode"] = fixture.returncode
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
                        (
                            "/work/native/huggingface-Repo2RLEnv-27d04ee/.venv/bin/python /work/native/pack_qcp_evidence.py && stat -c %s /work/native-evidence.tar.gz"
                            if args.stage == "qcp-independent"
                            else "tar -czf /work/native-evidence.tar.gz -C /evidence native && stat -c %s /work/native-evidence.tar.gz"
                        ),
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
