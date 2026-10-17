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

TARGET = Path("solution/reference.py")
# The equivalent control computes DNA entropy independently and retains a native
# fallback for other inputs. Other public functions and grading assets are unchanged.
CASES = {
    "equivalent_dna_entropy_preserve_legacy": (
        "import math\n"
        "seq = seq.upper()\n"
        "if wsize <= 0 or wsize > len(seq) or any(base not in 'ACGT' for base in seq):\n"
        "    return _lcc_legacy_other_inputs(seq, wsize)\n"
        "return [sum(-p * math.log(p, 4) for base in 'ACGT' "
        "if (p := seq[i:i+wsize].count(base) / wsize) > 0) "
        "for i in range(len(seq) - wsize + 1)]",
        1,
    ),
    "wrong_constant_zero": ("return [0.0] * (len(seq) - wsize + 1)", 0),
    "wrong_whole_sequence": ("return [lcc_simp(seq)] * (len(seq) - wsize + 1)", 0),
}


def replace_return(source, expression):
    functions = [
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == "lcc_mult"
    ]
    if len(functions) != 1:
        raise ValueError("Expected exactly one lcc_mult function")
    function = functions[0]
    if [a.arg for a in function.args.args] != ["seq", "wsize"]:
        raise ValueError("Unexpected lcc_mult signature")
    body = function.body
    if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    if not body:
        raise ValueError("Expected an executable function body")
    lines = source.splitlines(keepends=True)
    legacy = ""
    if "_lcc_legacy_other_inputs" in expression:
        if "_lcc_legacy_other_inputs" in source:
            raise ValueError("Unexpected helper name collision")
        legacy = "".join(lines[function.lineno - 1 : function.end_lineno])
        legacy = legacy.replace("def lcc_mult(", "def _lcc_legacy_other_inputs(", 1)
    replacement = [" " * body[0].col_offset + line + "\n" for line in expression.splitlines()]
    lines[body[0].lineno - 1 : function.end_lineno] = replacement
    changed = "".join(lines) + ("\n\n" + legacy if legacy else "")
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
                "changed_submission_body": expression,
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
