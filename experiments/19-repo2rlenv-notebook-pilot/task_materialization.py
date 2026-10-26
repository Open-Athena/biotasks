"""Tasksmith session for explicit supplied inputs and a separately executed oracle."""

import hashlib
import json
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from materialization_environment import (
    binding,
    check_review,
    digest,
    effective_exclusions,
    exclusion_key,
    merge_exclusions,
    removal_receipt,
)
from materialization_protocol import Materialization
from model_profile import native_effort
from openai import AsyncOpenAI
from reference_replay import sha256
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget
from source_operations import check_operation_coverage, operation_inventory

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger

HERE = Path(__file__).parent


def candidate_repair_shell(shell, attempts):
    """Reserve exploratory tools for repairing an executed candidate."""

    async def repair_shell(command, timeout_sec=120):
        if not attempts:
            return (
                "No command executed. Submit a complete reference-based candidate first. "
                "The controller will execute it and report failures. Shell access then "
                "becomes available for final-environment inspection and repair. "
                "Use the supplied source and observations; "
                "leave independent scientific comparison to validation. If those inputs "
                "cannot support a candidate, submit a blocked disposition with the reason."
            )
        return await shell(command=command, timeout_sec=timeout_sec)

    return repair_shell


def recovered_author_files(directory):
    """Read an unchanged worker-authored draft; never synthesize missing code."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    files = {}
    for item in manifest["files"]:
        name = item["path"]
        if Path(name).name != name or name in files:
            raise ValueError("Invalid recovered author path")
        path = directory / name
        if (
            path.is_symlink()
            or path.stat().st_size != item["bytes"]
            or sha256(path) != item["sha256"]
        ):
            raise ValueError("Recovered author file identity mismatch")
        files[name] = path.read_text()
    if not files:
        raise ValueError("Empty recovered author draft")
    return {"provenance": manifest, "files": files}


def materialization_context(context, source, seconds):
    """Preserve scientific caveats and observations, but omit downstream grader work plans."""
    return {
        "specification": {
            "task_brief": context["specification"]["task_brief"],
            "review": context["specification"].get("review", ""),
        },
        "repeatability": context.get("repeatability"),
        "policy": context["policy"],
        "source_evidence": context["source_evidence"],
        "source_operations": operation_inventory(context["source_evidence"]["inputs/original.py"]),
        "reference_observations": context["reference_observations"],
        "paths": context["paths"],
        "original_inputs": json.loads((source / "trial/inputs-before.json").read_text()),
        "reference_seconds": seconds,
    }


async def run_materialization(
    *, session, context, root, config, endpoint, credential, deadline, complete=None
):
    config = {**config, "reasoning_effort": native_effort(config)}
    source = session.snapshot["directory"]
    context = materialization_context(context, source, config["reference_seconds"])
    repair_record = None
    repair_original = None
    if config.get("construction_repair_file"):
        from construction_repair import load_repair

        if (
            config.get("prior_author_files")
            or config.get("authoring_mode", "construct") != "construct"
        ):
            raise ValueError("Construction repair cannot reuse another authoring mode")
        repair_record = json.loads((HERE / config["construction_repair_file"]).read_text())
        repair_original = load_repair(repair_record, context)
        context["construction_repair"] = repair_record
        save_record(root / "construction-repair.json", repair_record)
    prior_files = config.get("prior_author_files")
    mode = config.get("authoring_mode", "finalize" if prior_files else "construct")
    if mode not in {"construct", "finalize"} or (mode == "finalize" and not prior_files):
        raise ValueError("Invalid materialization authoring mode or missing prior draft")
    finalize = mode == "finalize"
    if prior_files:
        context["prior_worker_draft"] = recovered_author_files(HERE / prior_files)
    ledger = RequestLedger(root / "requests.sqlite", {"materialize": Allowance(None, None)})
    budget = RunBudget(
        BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "materialize", "1"
    )
    client = None
    if complete is None:
        client = AsyncOpenAI(
            base_url=endpoint,
            api_key=credential,
            max_retries=0,
            timeout=config["request_timeout_seconds"],
            http_client=httpx.AsyncClient(follow_redirects=False),
        )
        complete = completion_transport(client)
    attempts = []
    repair_exclusions = (
        [item.model_dump() for item in repair_original.environment_review.additional_exclusions]
        if repair_original is not None and repair_original.environment_review is not None
        else []
    )
    applied_additions = []
    last_execution = None
    last_execution_key = None
    last_catalog = None

    async def validate(candidate):
        nonlocal applied_additions, last_execution, last_execution_key, last_catalog
        if candidate.disposition == "blocked":
            return
        if repair_original is not None:
            from construction_repair import check_candidate

            check_candidate(repair_original, candidate)
        check_operation_coverage(candidate, context["source_operations"])
        review = candidate.environment_review.model_dump() if candidate.environment_review else None
        if review is not None:
            if last_execution is None:
                raise ValueError("Execute an initial candidate before assessing its environment")
            check_review(review, last_execution)
        additional = (
            review["additional_exclusions"]
            if review
            else repair_exclusions
            if repair_original is not None
            else applied_additions
        )
        merged = merge_exclusions(
            session.snapshot.get("dependency_exclusions"),
            additional,
            already_applied=applied_additions,
        )
        scientific = candidate.model_dump(exclude={"environment_review"})
        execution_key = digest({"candidate": scientific, "exclusions": merged})
        if execution_key == last_execution_key:
            # An assessment alone changes neither science nor environment. Its
            # identities still have to match this actual controlled execution.
            effective_exclusions(
                session.snapshot.get("dependency_exclusions"),
                candidate.model_dump(),
                last_execution,
            )
            return
        folder = root / "materialization" / str(len(attempts) + 1)
        folder.mkdir(parents=True)
        record = candidate.model_dump()
        record["seconds"] = config["reference_seconds"]
        removed = {exclusion_key(row) for row in applied_additions}
        record["new_dependency_exclusions"] = {
            "files": [row for row in additional if exclusion_key(row) not in removed]
        }
        record["effective_dependency_exclusions"] = merged
        record["original_source"] = context["source_evidence"]["inputs/original.py"]
        # Inspection shares this operation's existing wall-time allowance. It
        # cannot mint a new deadline after derivation/oracle have completed.
        record["controlled_execution_deadline"] = min(
            deadline, time.time() + 2 * config["reference_seconds"] + 60
        )
        save_record(folder / "candidate.json", record)
        await session.remote.upload(
            folder / "candidate.json", "/work/grading-private/materialization.json"
        )
        for name in (
            "materialization_remote.py",
            "grading_remote.py",
            "dependency_assets.py",
            "asset_literal_inspection.py",
            "installed_asset_hints.py",
        ):
            await session.remote.upload(HERE / name, "/work/" + name)
        # Any fresh attempt can replace the remote products, even if it fails.
        # A prior successful candidate can no longer reuse those paths blindly.
        last_execution_key = None
        started = time.time()
        reply = await session.command(
            ["python", "/work/materialization_remote.py"],
            2 * config["reference_seconds"] + 60,
            "materialize-" + str(len(attempts) + 1),
        )
        result = {"controller": reply, "elapsed_seconds": time.time() - started}
        attempts.append(result)
        if reply["exit_code"] == 0:
            result["execution"] = json.loads(reply["log"])
            if result["execution"].get("environment_removal_receipt") == removal_receipt(merged):
                applied_additions = additional
        save_record(folder / "result.json", result)
        if (
            reply["exit_code"]
            or result["execution"]["status"] != "executed_requires_scientific_validation"
        ):
            raise ValueError("Materialization/oracle execution failed: " + json.dumps(result))
        if repair_record is not None:
            from construction_repair import check_execution

            check_execution(repair_record, result["execution"])
        last_execution = result["execution"]
        last_catalog = folder / "dependency-assets-final.json"
        await session.remote.download(
            "/work/grading-private/dependency-assets-final.json", last_catalog
        )
        catalog = last_execution["environment"]["asset_catalog"]
        if (
            last_catalog.stat().st_size != catalog["bytes"]
            or sha256(last_catalog) != catalog["sha256"]
        ):
            raise ValueError("Final installed-asset catalog identity mismatch")
        hints_file = folder / "asset-value-hints.json"
        await session.remote.download("/work/grading-private/asset-value-hints.json", hints_file)
        hint_record = last_execution["environment"]["asset_value_hints"]
        if (
            hints_file.stat().st_size != hint_record["bytes"]
            or sha256(hints_file) != hint_record["sha256"]
        ):
            raise ValueError("Final installed-value hints identity mismatch")
        hints = json.loads(hints_file.read_text())
        if (
            hints["source"]
            != {
                "asset_catalog_sha256": catalog["sha256"],
                "reference_inventory_sha256": hashlib.sha256(
                    json.dumps(last_execution["reference"]).encode()
                ).hexdigest(),
            }
            or len(hints["findings"]) != hint_record["finding_count"]
            or hints["source"] != hint_record["source"]
        ):
            raise ValueError("Installed-value hints do not describe this execution")
        last_execution_key = execution_key
        try:
            effective_exclusions(
                session.snapshot.get("dependency_exclusions"),
                candidate.model_dump(),
                last_execution,
            )
        except ValueError as error:
            raise ValueError(
                str(error)
                + "\nControlled science execution succeeded. Inspect actual installed asset "
                "candidates against ALL final outputs, including recovered endpoints. "
                "Submit an evidence-backed environment_review; matches alone do not prove "
                "answer relevance or unused status. Additional exclusions require exact "
                "distribution/path/SHA256/reason and trigger fresh controlled execution. "
                "The original source, inputs, methods and selected endpoints stay fixed. "
                "Current observations: "
                + json.dumps(
                    {
                        **binding(last_execution),
                        "asset_summary": last_execution["environment"]["asset_summary"],
                        "asset_value_hints": last_execution["environment"].get("asset_value_hints"),
                        "already_applied_additional_exclusions": applied_additions,
                        "working_reference_outputs": "/work/author/derive-case/bundle/reference",
                        "installed_asset_catalog": "/work/construction-inspection/dependency-assets-final.json",
                        "installed_asset_value_hints": "/work/construction-inspection/asset-value-hints.json",
                    }
                )
            ) from error

    try:
        candidate = await stage(
            schema=Materialization,
            name="materialize",
            prompt_name="notebook-task-materialization-repair"
            if repair_record is not None
            else "notebook-task-finalize"
            if finalize
            else "notebook-task-materialize",
            context=context,
            root=root / "materialize",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "materialize"),
            complete=complete,
            deadline=deadline,
            limits=ChatLimits(
                max_output_tokens=None,
                max_input_bytes=None,
                max_response_bytes=None,
                tool_output_chars=None,
                reasoning_effort=native_effort(config),
                request_timeout_sec=config["request_timeout_seconds"],
            ),
            max_requests=None,
            validate=validate,
            shell=None if finalize else candidate_repair_shell(session.shell, attempts),
            shell_timeout_sec=config["reference_seconds"],
            recover_output_limit=False,
        )
        save_record(root / "materialization-candidate.json", candidate.model_dump())
        if candidate.disposition == "blocked":
            return {"status": "materialization_blocked"}
        execution = last_execution
        saved = root / "materialized"
        saved.mkdir(exist_ok=True)
        if last_catalog is None:
            raise ValueError("Missing final installed-asset catalog")
        (saved / "dependency-assets-final.json").write_bytes(last_catalog.read_bytes())
        for kind, remote_root in (
            ("inputs", "/work/grading-private/materialized/inputs"),
            ("reference", "/work/grading-private/materialized/reference"),
            ("oracle_outputs", "/task/outputs"),
        ):
            for item in execution[kind]:
                path = saved / kind / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                await session.remote.download(remote_root + "/" + item["path"], path)
                if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                    raise ValueError("Downloaded derived artifact identity mismatch")
        for name, content in [
            ("instruction.md", candidate.instruction),
            ("derive.py", candidate.derive_code),
            ("oracle.py", candidate.oracle_code),
            ("rationale.md", candidate.rationale),
        ]:
            (saved / name).write_text(content + "\n")
        save_record(saved / "manifest.json", execution)
        return {
            "status": "materialized_requires_scientific_validation",
            "materialization_attempts": len(attempts),
            "oracle_executed": True,
            "oracle_answers_isolated": True,
            "numerical_comparison_validated": False,
        }
    finally:
        if client:
            await client.close()
