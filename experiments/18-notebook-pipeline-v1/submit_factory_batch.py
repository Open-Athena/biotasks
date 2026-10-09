"""Submit a frozen authoring batch using private runtime configuration."""

import argparse
import hashlib
import json
import re
import sys
import termios
from pathlib import Path

from iris_factory_backend import IrisFactoryBackend

from biotasks.factory_budget import SessionBudget
from biotasks.factory_dispatch import dispatch


def main():
    from iris.cli.connect import connect_controller
    from iris.client.client import IrisClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--batch-sha256", required=True)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--private-config", type=Path, required=True)
    args = parser.parse_args()
    raw = args.batch.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.batch_sha256:
        raise ValueError("Frozen batch hash mismatch")
    batch = json.loads(raw)
    limits = json.loads(args.budget.read_text())
    if batch["concurrency"] != limits["concurrency"]:
        raise ValueError("Batch and budget concurrency differ")
    if len(batch["entries"]) != limits["seeds_per_batch"]:
        raise ValueError("Batch denominator differs from plan")
    for seed, spec in batch["entries"].items():
        if not re.fullmatch(r"[a-z0-9-]+", seed):
            raise ValueError("Unsafe seed identity")
        archive = args.archives / (seed + ".zip")
        digest = hashlib.sha256()
        with archive.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != spec["input_zip_sha256"]:
            raise ValueError("An input archive differs from the batch")
        if spec["request_cap"] > limits["maximum_model_requests_per_session"]:
            raise ValueError("Session exceeds request limit")
        if spec["wall_seconds"] > limits["session_wall_seconds"]:
            raise ValueError("Session exceeds wall limit")
    config = json.loads(args.private_config.read_text())
    ledger = SessionBudget(
        args.ledger,
        limits["maximum_new_sessions"],
        limits["maximum_new_sessions_per_seed"],
        limits["concurrency"],
    )
    if not sys.stdin.isatty():
        raise ValueError("Private credential handoff requires a terminal with echo disabled")
    original = termios.tcgetattr(sys.stdin.fileno())
    quiet = termios.tcgetattr(sys.stdin.fileno())
    quiet[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, quiet)
    print("READY_FOR_PRIVATE_HANDOFF", flush=True)
    try:
        token = json.loads(sys.stdin.readline())["GLM_BULK_TOKEN"]
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, original)
    workspace = Path(config["iris_workspace"])
    with connect_controller(config_file=Path(config["controller_config"])) as endpoint:
        with IrisClient.remote(
            endpoint.url,
            credentials=endpoint.credentials,
            workspace=workspace,
            bundle_exclude=re.compile(
                r"^(?:docs/|tests/|experiments/|examples/|\.agents/|\.claude/|infra/)"
            ),
        ) as client:
            backend = IrisFactoryBackend(
                client,
                Path(config["repository"]),
                Path(config["runtime"]),
                config["runtime_sha256"],
                Path(config["provider_config"]),
                config["provider_sha256"],
                token,
                config["endpoint_job"],
                config["artifact_prefix"],
                config["cluster"],
            )
            for seed in batch["entries"]:
                job = dispatch(
                    args.batch,
                    args.batch_sha256,
                    seed,
                    args.archives / (seed + ".zip"),
                    ledger,
                    backend,
                )
                print(json.dumps({"seed": seed, "job_id": job, "status": "submitted"}), flush=True)


if __name__ == "__main__":
    main()
