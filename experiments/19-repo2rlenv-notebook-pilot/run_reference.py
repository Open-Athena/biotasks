"""One source reference campaign: GLM preparation/review, offline Daytona run.

No task constructor, grading/quality campaign, solver or publication is invoked.
The Iris host holds credentials; generated code runs only inside Daytona.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import time
from pathlib import Path

import httpx
from daytona import CreateSandboxFromImageParams, Daytona, Resources
from openai import AsyncOpenAI
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.daytona import DaytonaWorker
from repo2rlenv.execution.daytona_cleanup import cleanup
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger
from design_stage import completion_transport
from preflight import PROBE, TARGETS
from reference_protocol import ReferencePlan, ReferenceReview, materialize
from reference_stage import stage


def check_config(config):
    if (
        not 0 < config["campaign_seconds"] <= 7200
        or config["max_repairs"] not in range(3)
        or not 0 < config["setup_seconds"] <= 1800
        or not 0 < config["reference_seconds"] <= 600
        or config["task"] != {"cpus": 4, "memory_gib": 8, "disk_gib": 10}
        or not 0 < float(config["daytona_budget_usd"]) <= 5
        or config["cleanup_seconds"] != 300
    ):
        raise ValueError("Reference campaign exceeds the checkpointed execution envelope")
    counts = [config["prepare_requests_per_pass"], config["review_requests_per_pass"]]
    if min(counts) < 3 or sum(counts) * (config["max_repairs"] + 1) != config["max_requests"]:
        raise ValueError("Stage request allowances must sum to the campaign ceiling")
    if config["max_requests"] > 80:
        raise ValueError("Request ceiling exceeds standing approval")


async def run(config, *, seed, root, deadline, endpoint, credential):
    check_config(config)
    root.mkdir(parents=True, exist_ok=False)
    experiment = Path(__file__).parent
    source = experiment / config["source_directory"]
    baseline = (source / "baseline.py").read_text()
    conversion = json.loads((source / "conversion.json").read_text())
    if (
        hashlib.sha256(baseline.encode()).hexdigest() != conversion["script_sha256"]
        or seed["source_sha256"] != conversion["source_sha256"]
    ):
        raise ValueError("Source/converted-script identity mismatch")
    save_record(root / "configuration.json", config)
    save_record(root / "conversion.json", conversion)
    (root / "baseline.py").write_text(baseline)
    passes = range(config["max_repairs"] + 1)
    allowances = {
        f"{kind}-{index}": Allowance(
            requests=config[f"{kind}_requests_per_pass"], output_tokens=config["max_output_tokens"]
        )
        for index in passes
        for kind in ("prepare", "review")
    }
    ledger = RequestLedger(root / "requests.sqlite", allowances)
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "reference", "1")
    limits = ChatLimits(
        max_output_tokens=config["max_output_tokens"],
        request_timeout_sec=config["request_timeout_seconds"],
    )
    client = AsyncOpenAI(
        base_url=endpoint,
        api_key=credential,
        max_retries=0,
        timeout=limits.request_timeout_sec,
        http_client=httpx.AsyncClient(follow_redirects=False),
    )
    complete = completion_transport(client)
    provider = Daytona()
    sandbox = None
    creation_started = False
    creation_confirmed = False
    owner = config["campaign"]
    setup_remaining = config["setup_seconds"]
    result = {
        "status": "started",
        "construction_run": False,
        "solver_run": False,
        "started": time.time(),
        "cleanup_verified": False,
    }
    feedback = []

    def dispatch(argv, timeout):
        if deadline - time.time() < timeout + config["cleanup_seconds"]:
            raise TimeoutError("Insufficient remaining time for operation and cleanup")
        # Explicit OS deadline bounds execution even if the provider response is lost.
        return worker.exec(
            ["timeout", "--signal=TERM", "--kill-after=5", str(timeout), *argv],
            timeout=timeout + 15,
        ).checked("Reference operation")

    def upload(path, name):
        worker.upload(path, "/work/" + name)

    def network(blocked, destination):
        sandbox.update_network_settings(network_block_all=blocked, request_timeout=30)
        sandbox.refresh_data(request_timeout=15)
        if sandbox.network_block_all is not blocked:
            raise RuntimeError("Provider network policy differs from requested state")
        probe = dispatch(["python", "-c", "TARGETS = " + repr(TARGETS) + "\n" + PROBE], 30)
        observations = json.loads(probe.stdout)
        save_record(
            destination,
            {
                "network_block_all": blocked,
                "probes": observations,
                "limitations": "Representative outbound TCP probes, not exhaustive attestation",
            },
        )
        if any(row["reachable"] is blocked for row in observations):
            raise RuntimeError("Network probe did not establish the required state")

    async def call(schema, kind, index, context, validator=None):
        name = f"{kind}-{index}"
        prompt = "notebook-reference-prepare" if kind == "prepare" else "notebook-reference-review"
        return await stage(
            schema=schema,
            name=name,
            prompt_name=prompt,
            context=context,
            root=root / name,
            ledger=ledger,
            budget=AuthorBudget(budget, root / name / "charges", name),
            complete=complete,
            deadline=deadline - config["cleanup_seconds"],
            limits=limits,
            max_requests=allowances[name].requests,
            validate=validator,
        )

    try:
        # Keep the full reservation even after cleanup; do not invent actual charges.
        daytona_ledger = BudgetLedger(
            root / "daytona-budget.sqlite", limit_usd=config["daytona_budget_usd"]
        )
        daytona_ledger.reserve(
            owner, config["daytona_budget_usd"], "Full reference campaign reservation"
        )
        save_record(root / "sandbox-claim.json", {"owner": owner, "state": "creation_uncertain"})
        creation_started = True
        sandbox = provider.create(
            CreateSandboxFromImageParams(
                name="biotasks19-" + owner,
                image=config["base_image"],
                language="python",
                os_user="root",
                resources=Resources(cpu=4, memory=8, disk=10),
                labels={"repo2rlenv.job": owner},
                auto_stop_interval=30,
                auto_delete_interval=0,
                ttl_minutes=125,
                public=False,
            ),
            timeout=420,
        )
        creation_confirmed = True
        worker = DaytonaWorker(provider, sandbox)
        sandbox.refresh_data(request_timeout=15)
        resources = {key: getattr(sandbox, key) for key in ("cpu", "memory", "disk")}
        save_record(
            root / "sandbox-claim.json",
            {
                "owner": owner,
                "id": sandbox.id,
                "state": "created",
                "resources": resources,
                "image": config["base_image"],
            },
        )
        if resources != {"cpu": 4, "memory": 8, "disk": 10}:
            raise RuntimeError("Provider resources differ from the approved envelope")
        dispatch(["mkdir", "-p", "/work", "/inputs", "/work/logs"], 30)
        upload(experiment / "reference_remote.py", "remote.py")
        upload(experiment / "source-manifest.json", "source-manifest.json")
        network(False, root / "network-online.json")
        started = time.monotonic()
        staging = dispatch(
            ["python", "/work/remote.py", "stage-inputs", "/work/source-manifest.json"],
            min(setup_remaining, 300),
        )
        setup_remaining -= math.ceil(time.monotonic() - started)
        inputs = json.loads(staging.stdout)
        save_record(root / "staged-inputs.json", inputs)
        for index in passes:
            if setup_remaining <= 0:
                result["status"] = "setup_budget_exhausted"
                break
            context = {
                "source": seed,
                "baseline_script": baseline,
                "conversion": conversion,
                "staged_original_inputs": inputs,
                "limits": config,
                "setup_seconds_remaining": setup_remaining,
                "previous_feedback": feedback,
            }

            async def validate(plan):
                if plan.disposition == "prepare":
                    materialize(baseline, plan)

            plan = await call(ReferencePlan, "prepare", index, context, validate)
            directory = root / f"attempt-{index}"
            directory.mkdir()
            save_record(directory / "plan.json", plan.model_dump())
            if plan.disposition == "reject":
                result.update(status="worker_rejected", reason=plan.explanation)
                break
            script, diff = materialize(baseline, plan)
            (directory / "reference.py").write_text(script)
            (directory / "source.diff").write_text(diff)
            (directory / "setup.sh").write_text(plan.setup_sh)
            review = await call(
                ReferenceReview,
                "review",
                index,
                {**context, "plan": plan.model_dump(), "source_diff": diff},
            )
            save_record(directory / "review.json", review.model_dump())
            if review.decision == "reject":
                result.update(status="review_rejected", reason=review.rationale)
                break
            if review.decision == "revise":
                feedback.append({"plan": plan.model_dump(), "review": review.model_dump()})
                result["status"] = "review_revision_budget_exhausted"
                continue
            network(False, directory / "network-online.json")
            upload(directory / "setup.sh", "setup.sh")
            allowed = min(setup_remaining, int(deadline - time.time()) - 900)
            if allowed <= 0:
                raise TimeoutError("Setup allowance exhausted")
            setup = dispatch(
                [
                    "python",
                    "/work/remote.py",
                    "execute",
                    json.dumps(["sh", "-eu", "/work/setup.sh"]),
                    str(allowed),
                    "/work",
                    f"setup-{index}",
                ],
                allowed + 10,
            )
            execution = json.loads(setup.stdout)
            setup_remaining -= math.ceil(execution["elapsed_seconds"])
            worker.download(f"/work/logs/setup-{index}.log", directory / "setup.log")
            save_record(directory / "setup-result.json", execution)
            if execution["exit_code"] != 0:
                feedback.append(
                    {
                        "plan": plan.model_dump(),
                        "setup": execution,
                        "log_tail": (directory / "setup.log").read_text(errors="replace")[-20000:],
                    }
                )
                result["status"] = "setup_repair_budget_exhausted"
                continue
            # Fresh computation workspace and exact reviewed script; setup cannot
            # supply endpoint outputs or replace the controller's source artifact.
            dispatch(
                [
                    "sh",
                    "-eu",
                    "-c",
                    "rm -rf /work/run /work/outputs; mkdir /work/run /work/outputs",
                ],
                30,
            )
            upload(directory / "reference.py", "reference.py")
            upload(directory / "plan.json", "plan.json")
            # Restore the controller-owned helper after generated setup, and
            # verify that neither setup nor computation changed the real inputs.
            upload(experiment / "reference_remote.py", "remote.py")
            upload(root / "staged-inputs.json", "staged-inputs.json")
            before = dispatch(["python", "/work/remote.py", "verify-inputs"], 120)
            save_record(directory / "inputs-before.json", json.loads(before.stdout))
            network(True, directory / "network-offline.json")
            run_record = dispatch(
                [
                    "env",
                    "MPLBACKEND=Agg",
                    "OMP_NUM_THREADS=4",
                    "OPENBLAS_NUM_THREADS=4",
                    "MKL_NUM_THREADS=4",
                    "NUMEXPR_NUM_THREADS=4",
                    "POLARS_MAX_THREADS=4",
                    "RAYON_NUM_THREADS=4",
                    "python",
                    "/work/remote.py",
                    "execute",
                    json.dumps(["/work/venv/bin/python", "/work/reference.py"]),
                    str(config["reference_seconds"]),
                    "/work/run",
                    f"reference-{index}",
                ],
                config["reference_seconds"] + 10,
            )
            execution = json.loads(run_record.stdout)
            worker.download(f"/work/logs/reference-{index}.log", directory / "reference.log")
            save_record(directory / "execution.json", execution)
            after = dispatch(["python", "/work/remote.py", "verify-inputs"], 120)
            save_record(directory / "inputs-after.json", json.loads(after.stdout))
            pip = dispatch(["/work/venv/bin/python", "-m", "pip", "freeze", "--all"], 60)
            (directory / "environment.txt").write_text(pip.stdout)
            inventory = json.loads(
                dispatch(["python", "/work/remote.py", "inventory", "/work/plan.json"], 120).stdout
            )
            save_record(directory / "artifacts.json", inventory)
            total = sum(item.get("bytes", 0) for item in inventory["artifacts"])
            if total > config["artifact_download_ceiling_bytes"]:
                raise ValueError(
                    "Reference evidence exceeds transport budget; preserve the sandbox record"
                )
            for item in inventory["artifacts"]:
                if item["exists"]:
                    destination = directory / "outputs" / item["path"]
                    worker.download("/work/outputs/" + item["path"], destination)
                    with destination.open("rb") as stream:
                        downloaded = hashlib.file_digest(stream, "sha256").hexdigest()
                    if downloaded != item["sha256"]:
                        raise ValueError("Downloaded reference artifact checksum mismatch")
            if execution["exit_code"] == 0 and inventory["declared_artifacts_present"]:
                result.update(
                    status="reference_executed",
                    attempt=index,
                    semantic_fidelity_validated=False,
                    elapsed_seconds=execution["elapsed_seconds"],
                )
                break
            feedback.append(
                {
                    "plan": plan.model_dump(),
                    "execution": execution,
                    "artifacts": inventory,
                    "log_tail": (directory / "reference.log").read_text(errors="replace")[-20000:],
                }
            )
            result["status"] = "reference_repair_budget_exhausted"
    except BaseException as error:
        result.update(status="incomplete", error_type=type(error).__name__)
        raise
    finally:
        await client.close()
        try:
            # Downloaded evidence must survive the ephemeral Iris host as well
            # as the sandbox. Reuse the existing hash-verified private export.
            result.update(finished=time.time(), setup_seconds_remaining=setup_remaining)
            save_record(root / "result.json", result)
            from iris_bootstrap import export

            export(root, os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/") + "/reference")
        finally:
            try:
                cleaned = cleanup(owner, provider) if creation_started else {"passed": True}
                # A lost create response may still materialize after a list call.
                result["cleanup_verified"] = cleaned["passed"] and (
                    not creation_started or creation_confirmed
                )
                save_record(root / "cleanup.json", cleaned)
            finally:
                result.update(finished=time.time(), setup_seconds_remaining=setup_remaining)
                save_record(root / "result.json", result)
    if not result["cleanup_verified"]:
        raise RuntimeError("Owned resource cleanup needs reconciliation")
    return result


if __name__ == "__main__":
    config = json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text())
    seed = json.loads(Path(os.environ["BIOTASKS_SEED"]).read_text())[0]
    asyncio.run(
        run(
            config,
            seed=seed,
            root=Path("/evidence/reference"),
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
        )
    )
