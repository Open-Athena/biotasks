"""Prepare a frozen official/candidate comparison; no builds, models or jobs."""

import argparse
import sys
from copy import deepcopy
from pathlib import Path

from biotasks.validation import controller, planning
from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json
from index_policy import MARKER, POLICY, emitter, normalize

ROOT = Path(__file__).resolve().parent


def compare(config):
    for row in config["bound_files"]:
        require(sha(Path(row["path"])) == row["sha256"], "Comparison source/input changed")
    sys.path.insert(0, str(Path(config["handoff_helper"]).parent))
    import handoff

    generation = Path(config["generation_directory"])
    readback = read_json(generation / "readback.json")
    expected = [{**r, "mode": oct(r["mode"])[2:]} for r in readback["source_members"]]
    require(
        inventory(generation / "generation-source") == expected, "Original source members changed"
    )
    completed = read_json(Path(config["original_connector"]) / "result.json")
    require(completed["state"] == "complete", "Original lifecycle must finish first")
    require(
        read_json(generation / "cleanup-proof.json")["verified_empty"]
        and all(r["cleanup"]["verified_empty"] for r in completed["outcomes"]),
        "Original owned cleanup is not verified",
    )
    base = read_json(Path(config["base_handoff_config"]))
    native = handoff.source_api(
        Path(base["upstream_source"]),
        Path(base["upstream_manifest"]),
        Path(base["upstream_extra_modules"]),
    )
    output = Path(config["output_directory"])
    output.mkdir(parents=True, exist_ok=True)
    code = {Path(r["path"]).name: r["sha256"] for r in config["bound_files"]}
    frozen = output / "comparison-input.json"
    if frozen.exists():
        require(read_json(frozen) == config, "Existing comparison has different inputs")
    else:
        require(not any(output.iterdir()), "Unowned comparison output is not empty")
        write_json(frozen, config)
    configs, outcomes = {}, {}
    for variant in ("official-baseline", POLICY):
        local = deepcopy(base)
        local["output_directory"] = str(output / variant)
        local["comparison_variant"] = {"id": variant, "source_identity": code}
        local["validation_template"]["id"] = "issue47-local-" + variant
        configs[variant] = local
        with handoff.local_only():
            if variant == POLICY:
                with emitter(native):
                    outcomes[variant] = handoff.prepare(local, native)
            else:
                outcomes[variant] = handoff.prepare(local, native)
    require(
        outcomes[POLICY]["task_count"] == outcomes["official-baseline"]["task_count"],
        "Task count changed",
    )
    raw = Path(base["raw_exports"])
    original_prepared = Path(config["original_connector"]) / "prepared-local/handoff/prepared"
    baseline = output / "official-baseline/handoff/prepared"
    candidate = output / POLICY / "handoff/prepared"
    tasks, caches = handoff.cache_bindings(native, raw, Path(base["bootstrap_cache"]))
    original_renderer = native._build_clean_recipe
    comparisons = []
    for task in tasks:
        name = task.relative_to(raw)
        old, new = baseline / name, candidate / name
        before, after = inventory(old), inventory(new)
        b, a = {r["path"]: r for r in before}, {r["path"]: r for r in after}
        require(set(a) == set(b), "Task files changed")
        require(all(a[n]["mode"] == b[n]["mode"] for n in b), "Task file modes changed")
        changed = sorted(n for n in b if b[n] != a[n])
        require(
            set(changed) <= {"task.toml", "environment/Dockerfile"},
            "Original grading asset changed",
        )
        require(
            handoff.grading_contract(old / "task.toml")
            == handoff.grading_contract(new / "task.toml"),
            "Grading/resources/deadlines changed",
        )
        old_recipe = (old / "environment/Dockerfile").read_text()
        require(
            old_recipe == (original_prepared / name / "environment/Dockerfile").read_text(),
            "Baseline differs from original failed recipe",
        )
        image = native._bootstrap_image_refs([task])[0][0]
        entry = next(c for c in caches if c["image"] == image)
        saved = read_json(Path(base["bootstrap_cache"]) / entry["cache"])
        owner, repo = saved["repo"].split("/")
        original = original_renderer(owner, repo, saved)
        with emitter(native):
            altered = native._build_clean_recipe(owner, repo, saved)
        require(
            original is not None and old_recipe.count(original) == 1,
            "Ambiguous original recipe boundary",
        )
        expected_recipe = old_recipe.replace(original, altered, 1)
        require(
            (new / "environment/Dockerfile").read_text() == expected_recipe,
            "Undeclared Dockerfile delta",
        )
        commands = [
            {"original": c, "candidate": normalize(c)}
            for c in saved["rebuild_cmds"]
            if normalize(c) != c
        ]
        require(bool(commands) == (MARKER in altered), "Experimental variant marker differs")
        comparisons.append(
            {
                "task": str(name),
                "files": len(before),
                "changed_files": changed,
                "grading_assets_modes_resources_deadlines_preserved": True,
                "baseline_dockerfile_sha256": sha(old / "environment/Dockerfile"),
                "candidate_dockerfile_sha256": sha(new / "environment/Dockerfile"),
                "command_deltas": commands,
            }
        )
    manifest = deepcopy(
        read_json(Path(config["original_connector"]) / "validation-execution-manifest.json")
    )
    require(
        len(manifest["exports"]) == 1 and len(comparisons) == 1,
        "This reference comparison requires exactly one frozen task",
    )
    manifest["id"] = "issue47-" + POLICY
    manifest["archive"]["prefix"] = "research/47-bootstrap-recipe-state"
    manifest["exports"][0]["path"] = str(candidate / comparisons[0]["task"])
    manifest["exports"][0]["publication"]["review"] += (
        " Explicit experimental generic emitter apt-index-refresh-v1, separate from official baseline; original grading/assets/settings retained; no model/task repair."
    )
    path = output / "validation-execution-manifest.json"
    if path.exists():
        require(read_json(path) == manifest, "Execution policy changed")
    else:
        write_json(path, manifest)
    directory = output / "validation"
    plan = (
        controller.verify_plan(directory)
        if directory.exists()
        else planning.prepare(path, directory)
    )
    require(
        len(plan["tasks"]) == 1 and not plan["unsupported"],
        "Candidate does not meet original validation interface",
    )
    result = {
        "state": "prepared_and_planned",
        "policy": POLICY,
        "upstream_source_files_modified": False,
        "upstream_emitter_behavior_modified": True,
        "new_generation_or_model_calls": 0,
        "remote_jobs": 0,
        "reference_source_members_reverified": len(expected),
        "comparison": comparisons,
        "validation_plan_identity": plan["plan_identity"],
        "configuration_sha256": json_sha(config),
        "resume_preserves_originals": True,
    }
    write_json(output / "comparison.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    print(__import__("json").dumps(compare(read_json(args.config)), indent=2))
