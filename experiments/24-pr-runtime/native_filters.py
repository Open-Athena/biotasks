"""Load only hash-verified native static filters without importing runtime clients.

This evaluates the original AST nodes from the declared upstream revision. It
does not initialize bootstrap, execute a task or establish runtime compatibility.
"""

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace

SOURCE_SHA256 = "0b748a897f1802fcaf4b59ab7ed54092c8715745b5dff14813c6389b1e134535"
CONSTANTS = {
    "_TEST_DIR_NAMES", "_DOC_PREFIX_DIRS", "_DIFF_HEADER_RE",
    "_NEW_TEST_FUNC_RE", "_NON_BUG_TITLE_RE",
}
FUNCTIONS = {
    "_path_is_test", "split_patch_and_test_patch", "_files_in_patch",
    "_count_new_test_funcs", "_is_non_bug_pr", "_word_count",
}
METHODS = {"_pre_filter", "_structural_quality_filter", "_lite_filter"}


def load(path: Path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Native source differs from the pinned #21 revision")
    original = ast.parse(raw)
    body = ast.parse("from __future__ import annotations\nimport re\n").body
    found = set()
    for node in original.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & CONSTANTS:
                body.append(node)
                found.update(names & CONSTANTS)
        elif isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
            body.append(node)
            found.add(node.name)
        elif isinstance(node, ast.ClassDef) and node.name == "PRRuntimePipeline":
            methods = [method for method in node.body
                       if isinstance(method, ast.FunctionDef) and method.name in METHODS]
            found.update(method.name for method in methods)
            node.body = methods
            body.append(node)
    if found != CONSTANTS | FUNCTIONS | METHODS:
        raise ValueError(f"Native extraction missing: {(CONSTANTS | FUNCTIONS | METHODS) - found}")
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(path), "exec"), namespace)
    pipeline = namespace["PRRuntimePipeline"]()
    pipeline.options = SimpleNamespace(
        skip_drafts=True, min_problem_statement_words=0, skip_ci_only=True,
        require_new_test_funcs=True, max_source_files_per_pr=50, lite_filter=False,
    )
    return pipeline, namespace


def pr_summary(row):
    return SimpleNamespace(
        is_draft=row["isDraft"], merged_at=row["mergedAt"],
        changed_files=row["changedFiles"], title=row["title"], body=row["body"],
    )
