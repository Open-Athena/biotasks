"""One remote pinned repository baseline; no model calls or mutations."""

import argparse
import json
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


def deadline(signum, frame):
    raise TimeoutError("Baseline execution deadline reached")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--profile", choices=("scikit-bio", "biopython"), default="scikit-bio")
    parser.add_argument("--biopython-fixture-copy", action="store_true")
    args = parser.parse_args()
    if args.biopython_fixture_copy and args.profile != "biopython":
        parser.error("Fixture-layout adaptation applies only to the Biopython profile")
    image = (
        "biotasks21-skbio-baseline"
        if args.profile == "scikit-bio"
        else "biotasks21-biopython-baseline"
    )
    test_path = (
        "skbio/diversity/alpha/tests/test_base.py"
        if args.profile == "scikit-bio"
        else "Tests/test_SeqUtils.py"
    )
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
    record = {
        "stage": "repository_baseline",
        "model_calls": 0,
        "status": "starting",
        "profile": args.profile,
        "test_path": test_path,
        "working_directory": "/workspace",
        "fixture_layout": "workspace_copy" if args.biopython_fixture_copy else "original",
    }
    worker = None
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, deadline)
    signal.alarm(7200)
    try:
        worker, receipt = provision_worker(spec, args.campaign / "workers", ledger, reserve_usd="5")
        prepare_docker(worker)
        worker.exec(["mkdir", "-p", "/work/baseline"], timeout=30).checked("mkdir")
        worker.upload(
            Path(__file__).with_name(f"{args.profile}-baseline.Dockerfile"),
            "/work/baseline/Dockerfile",
        )
        build = worker.exec(
            [
                "docker",
                "build",
                "--progress=plain",
                "-t",
                image,
                "/work/baseline",
            ],
            timeout=1800,
        )
        (args.campaign / "build.stdout").write_text(build.stdout)
        (args.campaign / "build.stderr").write_text(build.stderr)
        record["build_returncode"] = build.returncode
        build.checked("pinned repository build")
        details = worker.exec(["docker", "image", "inspect", image], timeout=30)
        (args.campaign / "image.json").write_text(details.stdout)
        command = (
            f"python -m pytest -o addopts= {test_path} "
            "-q --tb=short --junitxml=/tmp/results.xml; code=$?; "
            "cp /opt/baseline-freeze.txt /tmp/freeze.txt; exit $code"
        )
        if args.biopython_fixture_copy:
            command = (
                "mkdir -p GenBank && cp Tests/GenBank/NC_005816.gb GenBank/NC_005816.gb "
                "&& cmp Tests/GenBank/NC_005816.gb GenBank/NC_005816.gb "
                "&& sha256sum Tests/GenBank/NC_005816.gb GenBank/NC_005816.gb "
                "> /tmp/fixture-hashes.txt && " + command
            )
        record["test_command"] = command
        result = worker.exec(
            [
                "docker",
                "run",
                "--name",
                "biotasks21-baseline-test",
                "--network",
                "none",
                "--cpus",
                "1",
                "--memory",
                "2048m",
                "--pids-limit",
                "256",
                image,
                "sh",
                "-c",
                command,
            ],
            timeout=600,
        )
        (args.campaign / "test.stdout").write_text(result.stdout)
        (args.campaign / "test.stderr").write_text(result.stderr)
        record["test_returncode"] = result.returncode
        state = worker.exec(["docker", "inspect", "biotasks21-baseline-test"], timeout=30)
        record["container_state"] = json.loads(state.stdout)[0]["State"]
        for name in ("results.xml", "freeze.txt", "fixture-hashes.txt"):
            copied = worker.exec(
                ["docker", "cp", f"biotasks21-baseline-test:/tmp/{name}", f"/work/baseline/{name}"],
                timeout=30,
            )
            if copied.returncode == 0:
                worker.download(f"/work/baseline/{name}", args.campaign / name)
        record["status"] = "tests_passed" if result.returncode == 0 else "tests_failed"
    except BaseException as exc:
        record.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        save_record(args.campaign / "result.json", record)
        if worker is not None:
            record["cleanup"] = stop_worker(receipt, ledger)["state"]
            save_record(args.campaign / "result.json", record)


if __name__ == "__main__":
    main()
