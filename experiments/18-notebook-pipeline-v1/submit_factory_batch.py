"""Submit a frozen authoring batch using private runtime configuration."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import termios
from pathlib import Path

from iris_factory_backend import IrisFactoryBackend

from biotasks.factory_batch import execution_limits
from biotasks.factory_budget import SessionBudget
from biotasks.factory_scheduler import resume_batch


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
    limits = execution_limits(batch, args.budget.read_bytes())
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
    config = json.loads(args.private_config.read_text())
    ledger = SessionBudget(
        args.ledger,
        limits["maximum_seed_jobs"]
        if batch.get("execution_mode") == "seed_pipeline"
        else limits["maximum_new_sessions"],
        1
        if batch.get("execution_mode") == "seed_pipeline"
        else limits["maximum_new_sessions_per_seed"],
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
    daytona_key = None
    if batch.get("execution_mode") == "seed_pipeline":
        daytona_key = subprocess.run(
            config["daytona_credential_command"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
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
                daytona_key=daytona_key,
            )
            from iris.cluster.types import JobName

            def observe(job_id):
                state = client.job(JobName.from_string(job_id)).status().state.name.lower()
                if state in {"succeeded", "failed", "killed"}:
                    return state
                return "unknown"

            for record in resume_batch(
                args.batch, args.batch_sha256, args.archives, ledger, backend, observe
            ):
                print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
