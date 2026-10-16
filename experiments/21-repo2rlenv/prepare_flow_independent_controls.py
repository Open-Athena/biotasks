"""Prepare explicit oracle-submission controls, preserving the native grader.

These derived bundles are diagnostic fixtures, never new generated tasks or
blind solver attempts. The original exported bundle is left untouched.
"""

import argparse
import ast
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import tomli_w
from repo2rlenv.emitter.bundle import inspect_bundle

TARGET = Path("solution/reference/skbio/diversity/alpha/_base.py")
CASES = {
    "equivalent_nonzero_count": ("int(np.count_nonzero(_validate_counts_vector(counts)))", 1),
    "wrong_counts_zeros": ("len(counts)", 0),
    "wrong_constant": ("0", 0),
}


def replace_return(source, expression):
    functions = [
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == "observed_features"
    ]
    if len(functions) != 1:
        raise ValueError("Expected exactly one observed_features function")
    returns = [n for n in functions[0].body if isinstance(n, ast.Return)]
    if len(returns) != 1 or returns[0].lineno != returns[0].end_lineno:
        raise ValueError("Expected one single-line return")
    lines = source.splitlines(keepends=True)
    node = returns[0]
    lines[node.lineno - 1] = " " * node.col_offset + "return " + expression + "\n"
    changed = "".join(lines)
    ast.parse(changed)
    return changed


def retained_hashes(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Linked task assets are unsupported")
        if path.is_file() and path.relative_to(root) not in (TARGET, Path("task.toml")):
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    identity = inspect_bundle(args.task)
    if not identity["integrity_passed"]:
        raise ValueError("Original native bundle integrity check failed")
    source = (args.task / TARGET).read_text()
    retained = retained_hashes(args.task)
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for name, (expression, reward) in CASES.items():
        destination = args.output / name
        shutil.copytree(args.task, destination)
        (destination / TARGET).write_text(replace_return(source, expression))
        config_path = destination / "task.toml"
        config = tomllib.loads(config_path.read_text())
        config["task"]["name"] += "-control-" + name
        metadata = config["metadata"]["repo2env"]
        metadata.pop("evaluation", None)
        metadata.update(
            quality_status="diagnostic_control_only",
            source_bundle_hash=identity["bundle_hash"],
            diagnostic_control=name,
        )
        config_path.write_text(tomli_w.dumps(config))
        metadata["bundle_hash"] = inspect_bundle(destination)["bundle_hash"]
        config_path.write_text(tomli_w.dumps(config))
        derived = inspect_bundle(destination)
        assert derived["integrity_passed"]
        assert retained_hashes(destination) == retained
        records.append(
            {
                "case": name,
                "expected_reward": reward,
                "bundle": str(destination),
                "bundle_hash": derived["bundle_hash"],
                "changed_submission_expression": expression,
            }
        )
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "stage": "prepared_unexecuted_controls",
                "source_bundle_hash": identity["bundle_hash"],
                "unchanged_asset_hashes": retained,
                "cases": records,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
