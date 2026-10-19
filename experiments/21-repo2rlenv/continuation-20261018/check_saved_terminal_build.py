"""Exercise actual frozen design identities and prevent consumed-seed replay offline."""

import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from run_saved_terminal_build import prepare, seed_hash
from repo2rlenv.spec.input import GenerationInput

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
proof = json.loads((BASE / "saved-terminal-stage-reconciliation.json").read_text())
checks = []
with tempfile.TemporaryDirectory(prefix="biotasks21-stage-check-") as temporary:
    folder = Path(temporary)
    for recipe in ("seta_seed2synth", "seta_evol"):
        row = next(row for row in proof["rows"] if row["recipe"] == recipe)
        args = SimpleNamespace(recipe=recipe, designs=ROOT / row["design_source"],
            source=ROOT / ("seeds/seta-genomic-intervals/seeds.json" if recipe == "seta_seed2synth" else "seeds/pr2633-parent-v1/parent"),
            stage_proof=folder / "proof.json", parent_manifest=ROOT / "seeds/pr2633-parent-v1/manifest.json")
        spec = GenerationInput.model_validate({
            "source": {"kind": "seeds" if recipe == "seta_seed2synth" else "task", "path": str(args.source)},
            "pipeline": {"name": "terminal_synth" if recipe == "seta_seed2synth" else "task_evolve", "recipe": recipe},
            "llm": {"provider": "openai", "model": "glm-5.3", "endpoint": "https://example.invalid/v1", "api_key_env": "FIXTURE_KEY", "max_concurrent": 1, "timeout_sec": 1200},
            "execution": {"worker_receipt": str(folder / "worker.json"), "runtime_wheel": str(folder / "fixture.whl"), "campaign_dir": str(folder / "campaign"), "run_id": "offline", "timeout_sec": 6600},
            "output": {"destination": str(folder / "tasks"), "org": "open-athena", "dataset_name": "fixture"},
        })
        args.stage_proof.write_text(json.dumps(proof))
        _, options, seeds, designer, _, _ = prepare(args, spec)
        assert len(seeds) == 1 and seed_hash(seeds[0]) == row["pending_first_build_seed_sha256"][0]
        assert (options.target, options.max_candidates, options.max_repairs) == (1, 1, 2)
        design = designer(seeds[0], model=None, ledger=None, receipt=folder / (recipe + ".json"), operation_id="offline", resume=False)
        original = next(r["design"] for r in json.loads(args.designs.read_text())["records"] if r["seed_sha256"] == seed_hash(seeds[0]))
        assert all(design.model_dump()[key] == value for key, value in original.items())
        checks.append(recipe + ":exact_pending_seed_and_unchanged_design")
        for bad_hash, label in ((row["do_not_replay_seed_sha256"][0], "consumed"), ("0" * 64, "unknown")):
            changed = copy.deepcopy(proof)
            next(r for r in changed["rows"] if r["recipe"] == recipe)["pending_first_build_seed_sha256"] = [bad_hash]
            args.stage_proof.write_text(json.dumps(changed))
            try:
                prepare(args, spec)
            except AssertionError:
                checks.append(recipe + ":reject_" + label)
            else:
                raise AssertionError("Accepted " + label + " seed")
        args.stage_proof.write_text(json.dumps(proof))
        changed_design = folder / "changed-design.json"
        changed_design.write_bytes(args.designs.read_bytes() + b" ")
        args.designs = changed_design
        try:
            prepare(args, spec)
        except AssertionError:
            checks.append(recipe + ":reject_changed_design_bytes")
        else:
            raise AssertionError("Accepted changed design bytes")
report = {"stage": "offline_frozen_input_and_replay_guard_checks", "checks_passed": checks,
          "model_calls": 0, "remote_workers": 0, "target_code_execution": False}
(BASE / "saved-terminal-stage-offline-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
