"""Bound shared-reader plumbing without changing existing scientific policy."""

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

BASE = "9d0e6f3afa7378e7d9ca651e36e6507cf1345b03"
EXP = Path(__file__).resolve().parents[2]
ROOT = EXP.parents[1]
PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
PROMPT_ADDITION = """When `artifact_interface.parsing_support` is present, its optional
`read_delimited_table` helper is available beside the executed grader. The input
includes its exact source and a shell import path. Prefer it for ordinary
delimited tables rather than inventing another parser. It returns header and
rows as unstripped strings with consistent widths; scientific checks remain
yours. Enable `allow_blank_records` or an alternative encoding only when your
public acceptance rules permit it. Empty records are distinct from quoted empty
fields or delimiter-only rows. Verify every promised representation through
the actual reader; using this helper alone does not validate a comparison.
"""


def original(name):
    return subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT)


def same(before, after):
    assert ast.dump(ast.parse(before)) == ast.dump(after), "Unexplained policy/code change"


def remove_import(tree):
    found = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "grader_support"]
    assert len(found) == 1
    tree.body.remove(found[0])


def remove_block(tree, text):
    expected = ast.parse(text).body
    count = 0

    class Remove(ast.NodeTransformer):
        def generic_visit(self, node):
            nonlocal count
            for _, values in ast.iter_fields(node):
                if not isinstance(values, list):
                    continue
                for start in range(len(values) - len(expected) + 1):
                    selected = values[start : start + len(expected)]
                    if all(isinstance(v, ast.stmt) for v in selected) and [
                        ast.dump(v) for v in selected
                    ] == [ast.dump(v) for v in expected]:
                        del values[start : start + len(expected)]
                        count += 1
                        break
            return super().generic_visit(node)

    Remove().visit(tree)
    assert count == 1, "Declared parsing-support block changed or disappeared"


def prove_session(before, after):
    tree = ast.parse(after)
    remove_import(tree)
    remove_block(tree, "parsing_support = capture_support(root)")
    remove_block(
        tree,
        """capture_support(self.root.parent)
await self.remote.upload(self.root.parent / MODULE, "/work/" + MODULE)
await self.remote.upload(self.root.parent / MANIFEST, "/work/grading-private/" + MANIFEST)
sealed_support = await self.command(["chmod", "444", "/work/" + MODULE], 30, "seal-parsing-support")
if sealed_support["exit_code"]:
    raise RuntimeError("Cannot seal factory parsing support")
""",
    )
    remove_block(
        tree,
        """support = load_support(self.root.parent)
if support is not None and reply.get("parsing_support") != support:
    raise ValueError("Executed grader used different or unrecorded parsing support")
""",
    )

    class Interface(ast.NodeTransformer):
        expressions = 0
        fields = 0

        def visit_BinOp(self, node):
            if (
                isinstance(node.right, ast.Dict)
                and len(node.right.keys) == 1
                and isinstance(node.right.keys[0], ast.Constant)
                and node.right.keys[0].value == "parsing_support"
            ):
                assert isinstance(node.op, ast.BitOr)
                assert ast.dump(node.right.values[0]) == ast.dump(
                    ast.parse("support_interface(root)", mode="eval").body
                )
                assert (
                    isinstance(node.left, ast.Call)
                    and isinstance(node.left.func, ast.Name)
                    and node.left.func.id == "artifact_interface"
                )
                self.expressions += 1
                return node.left
            return self.generic_visit(node)

        def visit_Dict(self, node):
            self.generic_visit(node)
            for i, (key, value) in enumerate(zip(node.keys, node.values, strict=True)):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "parsing_support"
                    and isinstance(value, ast.Name)
                    and value.id == "parsing_support"
                ):
                    del node.keys[i]
                    del node.values[i]
                    self.fields += 1
                    break
            return node

    change = Interface()
    change.visit(tree)
    assert change.expressions == change.fields == 1
    same(before, tree)


def prove_remote(before, after):
    tree = ast.parse(after)
    function = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "stage_parsing_support"
    ]
    assert len(function) == 1
    tree.body.remove(function[0])
    remove_block(tree, 'TABLE_SUPPORT = Path("/work/biotasks_table_io.py")')
    remove_block(tree, 'record["parsing_support"] = stage_parsing_support()')
    same(before, tree)


def prove_bundle(before, after):
    tree = ast.parse(after)
    remove_import(tree)
    remove_block(
        tree,
        """support = load_support(grading, result.get("parsing_support"))
if support is not None:
    if any(c["execution"].get("parsing_support") != support for c in controls):
        raise ValueError("Control parsing support differs from its packaged source")
    assets["tests/" + MODULE] = TaskFile((grading / MODULE).read_bytes())
    assets["tests/" + MANIFEST] = TaskFile((grading / MANIFEST).read_bytes())
""",
    )
    same(before, tree)


def prove_gate(before, after):
    tree = ast.parse(after)
    remove_import(tree)
    remove_block(
        tree,
        """support = load_support(grading, result.get("parsing_support"))
assert load_support(task / "tests", support) == support
if support is not None:
    assert (task / "tests" / MODULE).read_bytes() == (grading / MODULE).read_bytes()
    assert read(task / "tests" / MANIFEST) == support
    assert all(c["execution"].get("parsing_support") == support for c in controls)
""",
    )
    same(before, tree)


def prove_prompt(before, after):
    assert after.count(PROMPT_ADDITION.encode()) == 1
    assert after.replace(PROMPT_ADDITION.encode(), b"", 1) == before


CHECKS = {
    PREFIX + "grading_session.py": prove_session,
    PREFIX + "grading_remote.py": prove_remote,
    PREFIX + "scientific_bundle.py": prove_bundle,
    PREFIX + "check_scientific_release.py": prove_gate,
    "src/biotasks/prompts/notebook-grader-author.md": prove_prompt,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    assert not args.proof.exists()
    changes = {}
    for name, check in CHECKS.items():
        before, after = original(name), (ROOT / name).read_bytes()
        check(before, after)
        changes[name] = {
            "before": hashlib.sha256(before).hexdigest(),
            "after": hashlib.sha256(after).hexdigest(),
        }
    proof = {
        "base_revision": BASE,
        "controller_changes": changes,
        "existing_scientific_rules_model_time_repair_resource_policy_preserved": True,
        "new_checks_add_support_identity_requirements": True,
        "new_reader_chooses_no_scientific_comparison": True,
        "live_qualification": False,
        "new_model_calls": 0,
    }
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
