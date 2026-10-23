"""Replay a verified, generated reference without authoring or scientific edits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reference_environment import setup_script, validate_environment
from reference_protocol import materialize
from replay_tables import observe_tables
from repo2rlenv.execution.lifecycle import save_record


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_dependency_exclusions(directory, recorded):
    """Bind the declared removals to the successful cleaned reference environment."""
    from dependency_assets import validate_manifest

    declaration = "candidate/dependency-exclusions.json"
    if declaration not in recorded:
        if (directory / declaration).exists():
            raise ValueError("Unrecorded dependency exclusion declaration")
        return None  # Historical recipe: no removal policy was declared.
    for name in [
        declaration,
        "trial/dependency_assets.py",
        "trial/dependency-exclusions-applied.json",
    ]:
        if name not in recorded or sha256(directory / name) != recorded[name]:
            raise ValueError("Dependency exclusion evidence identity mismatch")
    value = validate_manifest(
        json.loads((directory / declaration).read_text()), require_reason=True
    )
    receipt = json.loads((directory / "trial/dependency-exclusions-applied.json").read_text())
    expected = [
        {key: item[key] for key in ("distribution", "path", "sha256")} for item in value["files"]
    ]
    if receipt != {"files": expected, "excluded_files_absent": True}:
        raise ValueError("Dependency exclusions do not match the successful environment")
    return value


def load_snapshot(directory, prepared):
    directory = directory.resolve()
    manifest = json.loads((directory / "artifact-manifest.json").read_text())
    recorded = {}
    for item in manifest["files"]:
        path = directory / item["path"]
        if not path.resolve().is_relative_to(directory) or not path.is_file():
            raise ValueError("Invalid reference evidence path")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError("Reference evidence identity mismatch: " + item["path"])
        recorded[item["path"]] = item["sha256"]
    required = {
        "candidate/pyproject.toml",
        "candidate/system-packages.json",
        "candidate/stage-inputs.sh",
        "candidate/analysis.py",
        "trial/reference.py",
        "trial/uv.lock",
        "trial/environment.txt",
        "trial/inputs-before.json",
        "trial/result.json",
        "inputs/plan.json",
        "inputs/original.py",
        "inputs/exports.py",
    }
    if not required <= recorded.keys():
        raise ValueError("Incomplete frozen reference evidence")
    if (directory / "inputs/original.py").read_text() != prepared.baseline:
        raise ValueError("Reference baseline differs from preparation")
    if (directory / "inputs/exports.py").read_text() != prepared.exports:
        raise ValueError("Reference exports differ from preparation")
    if json.loads((directory / "inputs/plan.json").read_text()) != prepared.plan.model_dump():
        raise ValueError("Reference inventory differs from preparation")
    script, _ = materialize((directory / "candidate/analysis.py").read_text(), prepared.plan)
    if (directory / "trial/reference.py").read_text() != script:
        raise ValueError("Recorded reference is not the analysis plus frozen exports")
    previous = json.loads((directory / "trial/result.json").read_text())
    if previous["status"] != "reference_executed" or previous["execution"]["exit_code"] != 0:
        raise ValueError("Reference snapshot has no successful execution")
    expected = previous["artifacts"]["artifacts"]
    if expected != manifest["large_outputs"]:
        raise ValueError("Output manifest differs from recorded execution")
    paths = [a["path"] for a in expected]
    if set(paths) != {a.path for a in prepared.plan.artifacts} or len(paths) != len(set(paths)):
        raise ValueError("Output inventory differs from preparation")
    packages = json.loads((directory / "candidate/system-packages.json").read_text())
    validate_environment((directory / "candidate/pyproject.toml").read_text(), packages)
    exclusions = load_dependency_exclusions(directory, recorded)
    return {
        "directory": directory,
        "hashes": recorded,
        "outputs": expected,
        "system_packages": packages,
        "dependency_exclusions": exclusions,
    }


def compare_inventory(expected, actual):
    """Byte identity observations only; this function is not a scientific grader."""
    before = {item["path"]: item for item in expected}
    after = {item["path"]: item for item in actual}
    if len(after) != len(actual) or set(after) != set(before):
        raise ValueError("Replay changed the declared output inventory")
    return [
        {
            "path": name,
            "byte_identical": after[name].get("exists", False)
            and after[name].get("sha256") == item["sha256"],
            "baseline_sha256": item["sha256"],
            "replay_sha256": after[name].get("sha256"),
        }
        for name, item in before.items()
    ]


async def replay_reference(*, remote, snapshot, root, config):
    root.mkdir(parents=True, exist_ok=False)
    source = snapshot["directory"]
    save_record(root / "frozen-inputs.json", {"sha256": snapshot["hashes"]})
    setup = root / "setup.sh"
    setup.write_text(
        setup_script(
            snapshot["system_packages"],
            verify_inputs=False,
            locked=True,
            dependency_cleanup=snapshot.get("dependency_exclusions") is not None,
        )
    )
    initialized = await remote.command(
        ["mkdir", "-p", "/work/environment", "/work/cache", "/inputs"],
        30,
        "replay-initialize",
    )
    if initialized["exit_code"]:
        raise RuntimeError("Replay initialization failed")
    for local, target in [
        (source / "candidate/pyproject.toml", "/work/environment/pyproject.toml"),
        (source / "trial/uv.lock", "/work/environment/uv.lock"),
        (source / "candidate/stage-inputs.sh", "/work/stage-inputs.sh"),
        (setup, "/work/setup.sh"),
        (source / "trial/reference.py", "/work/reference.py"),
        (source / "inputs/plan.json", "/work/plan.json"),
        (source / "trial/inputs-before.json", "/work/expected-inputs.json"),
    ]:
        await remote.upload(local, target)
    if snapshot.get("dependency_exclusions") is not None:
        await remote.upload(
            source / "candidate/dependency-exclusions.json",
            "/work/environment/dependency-exclusions.json",
        )
        await remote.upload(source / "trial/dependency_assets.py", "/work/dependency_assets.py")
    await remote.network(False)
    built = await remote.command(
        ["sh", "-eu", "/work/setup.sh"], config["setup_seconds"], "replay-setup"
    )
    save_record(root / "setup-result.json", built)
    if built["exit_code"]:
        raise RuntimeError("Frozen setup failed; no automatic repair or resolution")
    for name in ("uv.lock", "environment.txt"):
        await remote.download("/work/environment/" + name, root / name)
        if sha256(root / name) != snapshot["hashes"]["trial/" + name]:
            raise RuntimeError("Resolved replay environment differs from the reference: " + name)
    if snapshot.get("dependency_exclusions") is not None:
        name = "dependency-exclusions-applied.json"
        await remote.download("/work/environment/" + name, root / name)
        if sha256(root / name) != snapshot["hashes"]["trial/" + name]:
            raise RuntimeError("Replay dependency removal differs from the reference")
    await remote.network(True)
    trials = []
    for number in range(1, config["max_tests"] + 1):
        trial = root / "trials" / str(number)
        trial.mkdir(parents=True)
        reset = await remote.command(
            ["sh", "-eu", "-c", "rm -rf /work/run /work/outputs; mkdir /work/run /work/outputs"],
            30,
            f"replay-reset-{number}",
        )
        if reset["exit_code"]:
            raise RuntimeError("Cannot establish a fresh replay workspace")
        # Restore immutable controller inputs on every invocation.
        for name, target in [
            ("trial/reference.py", "/work/reference.py"),
            ("inputs/plan.json", "/work/plan.json"),
            ("trial/inputs-before.json", "/work/expected-inputs.json"),
        ]:
            await remote.upload(source / name, target)
        await remote.helper(
            ["verify-staging", "/work/expected-inputs.json"], f"replay-inputs-before-{number}"
        )
        record = {"status": "incomplete", "number": number}
        try:
            record["execution"] = await remote.command(
                ["env", "MPLBACKEND=Agg", "/work/venv/bin/python", "/work/reference.py"],
                config["reference_seconds"],
                f"replay-reference-{number}",
                cwd="/work/run",
            )
            await remote.upload(source / "trial/inputs-before.json", "/work/expected-inputs.json")
            await remote.helper(
                ["verify-staging", "/work/expected-inputs.json"], f"replay-inputs-after-{number}"
            )
            await remote.upload(source / "inputs/plan.json", "/work/plan.json")
            inventory = await remote.helper(
                ["inventory", "/work/plan.json"], f"replay-inventory-{number}"
            )
            record["artifacts"] = inventory
            for item in inventory["artifacts"]:
                if not item["exists"]:
                    continue
                target = trial / "outputs" / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                await remote.download("/work/outputs/" + item["path"], target)
                if sha256(target) != item["sha256"]:
                    raise RuntimeError("Replay artifact download identity mismatch")
            if record["execution"]["exit_code"] or not inventory["declared_artifacts_present"]:
                raise RuntimeError("Reference replay failed; preserve evidence without repair")
            record["comparison_to_original"] = compare_inventory(
                snapshot["outputs"], inventory["artifacts"]
            )
            observe_tables(
                record["comparison_to_original"], source / "trial/outputs", trial / "outputs"
            )
            if trials:
                record["comparison_to_previous"] = compare_inventory(
                    trials[-1]["artifacts"]["artifacts"], inventory["artifacts"]
                )
            record["status"] = "executed"
            trials.append(record)
        finally:
            save_record(trial / "result.json", record)
    observation = {
        "status": "repeatability_observed_requires_comparison_review",
        "reference_tests": len(trials),
        "model_calls": 0,
        "all_outputs_byte_identical_to_original": all(
            item["byte_identical"] for trial in trials for item in trial["comparison_to_original"]
        ),
        "all_output_differences_limited_to_table_serialization_or_row_order": all(
            item["byte_identical"]
            or item.get("table_observation", {}).get("same_header_and_row_multiset", False)
            for trial in trials
            for item in trial["comparison_to_original"]
        ),
        "output_observations": [trial["comparison_to_original"] for trial in trials],
        "comparison_rules_validated": False,
        "limitations": "Finite repeated runs, not a grading contract or portability proof. Fresh processes/workspaces share the rebuilt environment and caches; base image tag is reused, not an immutable image digest.",
    }
    save_record(root / "comparison.json", observation)
    return observation
