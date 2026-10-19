"""Continue only a never-built original design through the native terminal runner.

This is stage continuation, not design regeneration or task repair by Codex.
The enclosing TRC wrapper supplies the deadline, free GLM route and pinned wheel.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import signal
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from replay_parent_evolution import saved_designer as saved_evolution
from replay_seta_designs import saved_designer as saved_seta
from run_dataarc_build import deadline, recover_remote, verify_deleted
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.artifacts import check_runtime_wheel
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.pipelines.recipes.seta_evol import recipe as evolution
from repo2rlenv.pipelines.recipes.terminal.runner import load_seeds, run_synthesis
from repo2rlenv.pipelines.task_evolve import TaskEvolutionPipeline
from repo2rlenv.pipelines.terminal_synth import TerminalSynthesisPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import TaskEvolutionOptions, TerminalSynthesisOptions


def seed_hash(seed):
    return hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()


def prepare(args, spec):
    proof = json.loads(args.stage_proof.read_text())
    row = next(row for row in proof["rows"] if row["recipe"] == args.recipe)
    assert row["already_charged_candidates"] == 3
    assert row["new_candidate_charge_for_pending_build"] == 0
    assert hashlib.sha256(args.designs.read_bytes()).hexdigest() == row["design_source_sha256"]
    if args.recipe == "seta_seed2synth":
        seeds = load_seeds(args.source)
        options = TerminalSynthesisOptions(target=1, max_candidates=1, max_repairs=2)
        designer = saved_seta(args.designs, row["design_source_sha256"])
        pipeline = TerminalSynthesisPipeline(spec, options)
        extra = {}
    else:
        manifest = json.loads(args.parent_manifest.read_text())
        original_options = TaskEvolutionOptions.model_validate(manifest["recipes"]["seta_evol"]["options"])
        assert (original_options.target, original_options.max_candidates, original_options.max_repairs) == (3, 10, 2)
        seeds = evolution.load_parents(args.source, original_options)
        assert [seed_hash(seed) for seed in seeds] == [record["sha256"] for record in manifest["recipes"]["seta_evol"]["records"]]
        options = original_options.model_copy(update={"target": 1, "max_candidates": 1})
        designer = saved_evolution(args.designs, row["design_source_sha256"])
        pipeline = TaskEvolutionPipeline(spec, options)
        extra = {"builder_prompt": evolution.builder_prompt()}
    expected = set(row["pending_first_build_seed_sha256"])
    assert len(expected) == 1 and len(seeds) == 3
    assert len({seed_hash(seed) for seed in seeds}) == 3
    assert not expected.intersection(row["do_not_replay_seed_sha256"])
    selected = [seed for seed in seeds if seed_hash(seed) in expected]
    assert len(selected) == 1
    return pipeline, options, selected, designer, extra, row


def run(args):
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1":
        raise RuntimeError("Authorized remote controller required")
    capture = Path(os.environ["IRIS_OUTPUT_DIR"]).resolve()
    wheel_hash = check_runtime_wheel(args.wheel)
    settings = json.loads(args.adaptation.read_text())
    assert settings["stage"] == "generation_only" and not settings["paid_fallback"]
    assert settings["request_timeout_sec"] == 1200
    spec = GenerationInput.model_validate({
        "source": {"kind": "seeds" if args.recipe == "seta_seed2synth" else "task", "path": str(args.source.resolve())},
        "pipeline": {"name": "terminal_synth" if args.recipe == "seta_seed2synth" else "task_evolve", "recipe": args.recipe},
        "llm": {"provider": "openai", "model": "glm-5.3", "endpoint": os.environ["BIOTASKS21_GLM_ENDPOINT"],
                "api_key_env": "BIOTASKS21_GLM_KEY", "max_concurrent": 1, "timeout_sec": 1200, "fallback": None},
        "execution": {"worker_receipt": str((args.campaign / "pending-worker.json").resolve()),
                      "runtime_wheel": str(args.wheel.resolve()), "campaign_dir": str(args.campaign.resolve()),
                      "run_id": args.run_id, "timeout_sec": 6600, "resume": False},
        "output": {"destination": str((args.campaign / "tasks").resolve()), "org": "open-athena", "dataset_name": "biotasks21-" + args.recipe},
        "auth": {"use_gh_cli": False},
    })
    pipeline, options, selected, designer, extra, proof = prepare(args, spec)
    args.campaign.mkdir(parents=True, exist_ok=False)
    ledger = BudgetLedger(args.campaign / "budget.sqlite3", limit_usd="50")
    worker = None
    receipt = None
    state = {"stage": "never_built_saved_design_native_continuation", "recipe": args.recipe,
             "manual_task_fixes": 0, "external_task_feedback": False, "design_model_calls": 0,
             "new_candidate_charge": 0, "seed_sha256": seed_hash(selected[0]),
             "runtime_wheel_sha256": wheel_hash, "status": "starting"}
    save_record(args.campaign / "stage-settings.json", {"proof": proof, "native_options": options.model_dump(mode="json"), "adaptation": settings})
    try:
        worker, receipt = provision_worker(WorkerSpec(provider="daytona", cpus=2, memory_mb=4096, disk_gb=10,
            timeout_sec=7200, name=args.worker_name), args.campaign / "workers", ledger, reserve_usd="5")
        spec.execution.worker_receipt = receipt.resolve()
        save_record(args.campaign / "input-private.json", spec.model_dump(mode="json"))
        with adapted_authoring(settings, args.campaign, metering_target="terminal_builder"):
            result = run_synthesis(spec, options, Path(spec.output.destination), pipeline.on_event,
                                   inputs=selected, designer=designer, **extra)
        record = dataclasses.asdict(result)
        record["out_dir"] = str(result.out_dir)
        save_record(args.campaign / "native-result.json", record)
        state["status"] = "completed"
    except BaseException as exc:
        state.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        try:
            if receipt is not None:
                try:
                    recover_remote(worker, args.campaign)
                    state["remote_evidence_recovered"] = True
                except Exception as exc:
                    state.update(remote_evidence_recovered=False, remote_evidence_error_type=type(exc).__name__)
                finally:
                    try:
                        stop_worker(receipt, ledger)
                    except Exception as exc:
                        state["stop_error_type"] = type(exc).__name__
                    state["cleanup"] = verify_deleted(worker)
        finally:
            save_record(args.campaign / "controller-result.json", state)
            preserve(args.campaign, capture / "after-cleanup")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=("seta_seed2synth", "seta_evol"), required=True)
    for name in ("campaign", "source", "designs", "stage-proof", "wheel", "adaptation"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--parent-manifest", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--worker-name", required=True)
    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, deadline)
    timeout = int(os.environ.get("BIOTASKS21_CONTROLLER_DEADLINE", "6600"))
    assert 60 <= timeout <= 6900
    signal.alarm(timeout)
    run(parser.parse_args())
