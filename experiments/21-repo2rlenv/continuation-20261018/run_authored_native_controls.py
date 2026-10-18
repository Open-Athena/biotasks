"""Export a frozen authored candidate and exercise unchanged native grading.

Target execution is restricted to the approved remote worker. This is separate
from authoring, blind model evaluation, and independent task admission.
"""

import argparse
import ast
import hashlib
import json
import os
import shutil
import tarfile
import tomllib
from pathlib import Path, PurePosixPath

import tomli_w

from export_verify_smith import export_flow
from prepare_pr_correctness_controls import assets
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.repository.export import private_asset
from repo2rlenv.pipelines.recipes.swe_smith.export import export_candidate
from repo2rlenv.pipelines.recipes.swe_smith.options import SWESmithOptions
from repo2rlenv.spec.recipe_options import ReconstructionOptions
from run_robbins_native_controls import run_case


PROFILES = {
    "53ec5f51639d4053971f": {
        "recipe": "swe_smith",
        "source": "Bio/SeqUtils/lcc.py",
        "function": "lcc_mult",
        "negative_bodies": {
            "incorrect_zero": "return [0.0] * (len(seq) - wsize + 1)",
            "incorrect_constant_example": "return [0.9528195311147832] * (len(seq) - wsize + 1)",
        },
    },
    "3ad7ba60ca7686b2007b": {
        "recipe": "swe_flow",
        "source": "skbio/diversity/alpha/_base.py",
        "function": "enspie",
        "negative_bodies": {
            "incorrect_zero": "return 0.0",
            "incorrect_ignore_finite": "return inv_simpson(counts)",
        },
    },
}


def function_node(source, name):
    matches = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1:
        raise ValueError("Expected one selected top-level function")
    return matches[0]


def replace_body(source, name, body):
    node = function_node(source, name)
    statements = node.body
    if isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements = statements[1:]
    lines = source.splitlines(keepends=True)
    indent = " " * statements[0].col_offset
    lines[statements[0].lineno - 1:node.end_lineno] = [indent + line + "\n" for line in body.splitlines()]
    changed = "".join(lines)
    ast.parse(changed)
    return changed


def alternative_source(source, profile):
    if profile["function"] == "enspie":
        return replace_body(source, "enspie", "return 1.0 / dominance(counts, finite=finite)")
    node = function_node(source, "lcc_mult")
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "compone" and n.func.attr == "append"]
    if len(calls) != 1:
        raise ValueError("Expected the one native entropy-table construction")
    call = calls[0]
    if call.lineno != call.end_lineno:
        raise ValueError("Unexpected entropy-table source layout")
    # Independent base-2 entropy expression, preserving the existing rolling
    # algorithm and unrelated behavior, including native regression inputs.
    lines = source.splitlines(keepends=True)
    line = lines[call.lineno - 1]
    lines[call.lineno - 1] = line[:call.col_offset] + "compone.append(((i + 1) / wsize) * math.log2((i + 1) / wsize) / 2)" + line[call.end_col_offset:]
    changed = "".join(lines)
    ast.parse(changed)
    return changed


def expected_submitted_files(base, options):
    selected = set()
    for relative in options.source_paths:
        root = base / relative
        if not root.exists():
            raise ValueError("Missing configured native source path")
        for file in ([root] if root.is_file() else root.rglob("*.py")):
            path = PurePosixPath(file.relative_to(base).as_posix())
            if file.is_file() and file.suffix == ".py" and not private_asset(path, options):
                selected.add(str(path))
    return sorted(selected)


def prepare_cases(task, output, identifier, profile):
    original = assets(task)
    configuration = tomllib.loads((task / "task.toml").read_text())
    offline = output / "offline-task"
    shutil.copytree(task, offline)
    for phase in ("environment", "agent", "verifier"):
        configuration.setdefault(phase, {})["network_mode"] = "no-network"
    configuration["environment"].update(cpus=1, memory_mb=2048)
    metadata = configuration["metadata"]["repo2env"]
    metadata["original_content_hash"] = metadata.pop("content_hash", "")
    metadata["validation_profile"] = "explicit_offline_authored_source_controls_not_admission"
    (offline / "task.toml").write_text(tomli_w.dumps(configuration))
    compose = offline / "environment/docker-compose.yaml"
    if compose.is_file():
        compose.unlink()
    excluded = {"task.toml", "environment/docker-compose.yaml"}
    assert assets(task, exclude=excluded) == assets(offline, exclude=excluded)
    fixed = assets(offline, exclude={"solution/solve.sh"})
    source = (offline / "environment/source" / profile["source"]).read_text()
    alternative = alternative_source(source, profile)
    replacements = {"alternative": alternative, "alternative_repeat": alternative}
    replacements.update({name: replace_body(source, profile["function"], body) for name, body in profile["negative_bodies"].items()})
    rows = []
    for name in ["baseline", "native_reference", "alternative", "alternative_repeat", *profile["negative_bodies"]]:
        destination = output / "cases" / name
        shutil.copytree(offline, destination)
        if name == "baseline":
            script = "#!/bin/sh\nset -eu\n# Retain the defective/skeleton library.\n"
        elif name in replacements:
            program = "from pathlib import Path\nPath('/workspace/" + profile["source"] + "').write_text(" + repr(replacements[name]) + ")\n"
            script = "#!/bin/sh\nset -eu\npython3 - <<'PYCONTROL'\n" + program + "PYCONTROL\n"
        else:
            script = (offline / "solution/solve.sh").read_text()
        solve = destination / "solution/solve.sh"
        solve.write_text(script)
        solve.chmod(0o755)
        assert assets(destination, exclude={"solution/solve.sh"}) == fixed
        rows.append({"case": name, "bundle": str(destination), "expected_reward": int(name in ("native_reference", "alternative", "alternative_repeat"))})
    save_record(output / "control-manifest.json", {"stage": "prepared_not_executed", "candidate_id": identifier, "native_task_relative_path": task.relative_to(output).as_posix(), "native_assets": original, "profile_assets": assets(offline), "changed_profile_assets": sorted(excluded), "case_unchanged_assets": fixed, "cases": rows, "model_calls": 0, "reward_contract": "unchanged native binary all expected tests pass"})
    return rows, fixed


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Native target execution requires the approved remote worker")
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / "manifest.json").read_text())
    identifier = manifest["candidate_id"]
    profile = PROFILES[identifier]
    assert manifest["model_calls"] == 0 and profile["recipe"] == manifest["recipe"]
    for name, record in manifest["files"].items():
        with (args.inputs / name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == record["sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    unpacked = Path("/work/native/selected-generation")
    unpacked.mkdir(exist_ok=False)
    with tarfile.open(args.inputs / "generation-evidence.tar.gz") as archive:
        archive.extractall(unpacked, filter="data")
    generation = unpacked / "native/generation"
    candidates = json.loads((generation / "generation.json").read_text())["candidates"]
    candidate = next(c for c in candidates if c["id"] == identifier)
    authored = next(r for r in json.loads((args.inputs / "issues.json").read_text())["records"] if r["candidate_id"] == identifier)
    assert authored["status"] == "authored"
    options_type = SWESmithOptions if profile["recipe"] == "swe_smith" else ReconstructionOptions
    options = options_type.model_validate(json.loads((args.inputs / "config.json").read_text())["options"])
    if profile["recipe"] == "swe_smith":
        task = export_candidate(generation, candidate, options, authored["issue"], args.output / "native-task", org="open-athena")
    else:
        task = export_flow(generation, candidate, options, authored, args.output / "native-task")
    contract = json.loads((task / "tests/contract.json").read_text())
    assert sorted(contract["submitted_files"]) == expected_submitted_files(generation / "base", options)
    assert profile["source"] in contract["submitted_files"]
    expected_tests = set(candidate["contrast"]["FAIL_TO_PASS"] + candidate["contrast"]["PASS_TO_PASS"])
    assert set(contract["expected_passes"]) == expected_tests
    cases, fixed = prepare_cases(task, args.output, identifier, profile)
    records = []
    summary = {"stage": "authored_native_source_controls_not_admission", "candidate_id": identifier, "recipe": profile["recipe"], "model_calls": 0, "native_export_completed": True, "records": records, "independently_admitted": False}
    for case in cases:
        assert assets(Path(case["bundle"]), exclude={"solution/solve.sh"}) == fixed
        records.append(run_case(case, args.output, expected_tests))
        save_record(args.output / "summary.json", summary)
    summary.update(all_controls_passed=all(r["passed"] for r in records), all_controls_executed_and_parsed=all(r["executed_and_parsed"] for r in records))
    save_record(args.output / "summary.json", summary)
    print("BIOTASKS21_AUTHORED_NATIVE_CONTROLS " + json.dumps({"candidate_id": identifier, "all_controls_passed": summary["all_controls_passed"], "records": [{k: row.get(k) for k in ("case", "stage", "reward", "passed", "executed_and_parsed", "error_type")} for row in records]}), flush=True)
    if not summary["all_controls_executed_and_parsed"]:
        raise RuntimeError("Some native source controls did not execute and parse")


if __name__ == "__main__":
    main()
