"""Syntactic operation accounting, not execution tracing or scientific equivalence."""

import ast
import hashlib


def operation_inventory(source):
    rows = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            rows.append(
                {
                    "id": f"call-{node.lineno}-{node.col_offset}",
                    "line": node.lineno,
                    "column": node.col_offset,
                    "function": ast.unparse(node.func),
                    "source": ast.get_source_segment(source, node),
                }
            )
    return {
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "boundary": "Literal call sites, including nested/conditional/function-body calls; not a runtime DAG or an eligibility judgment. The worker must interpret source and narrative.",
        "operations": sorted(rows, key=lambda row: (row["line"], row["column"])),
    }


def check_operation_coverage(candidate, inventory):
    """Reject missing accounting or impossible declared counterpart relationships.

    Classifications and equivalence remain scientific claims for independent
    review. This guard does not infer scientific meaning from function names.
    """
    if candidate.disposition != "ready":
        return
    known = {item["id"]: item for item in inventory["operations"]}
    uses = {}
    outputs = set()
    for item in candidate.operation_coverage:
        if not item.operation_ids or len(set(item.operation_ids)) != len(item.operation_ids):
            raise ValueError("Each operation accounting group needs distinct source-call IDs")
        for identity in item.operation_ids:
            if identity not in known or identity in uses:
                raise ValueError("Account for each original source-call ID exactly once")
            uses[identity] = item
        paths = set(item.artifact_paths)
        if len(paths) != len(item.artifact_paths):
            raise ValueError("Duplicate coverage artifact path")
        if item.role == "result":
            if not paths or not paths <= set(candidate.output_paths):
                raise ValueError("Scientific-result coverage must name actual requested outputs")
            outputs |= paths
        elif item.role == "supplied_input":
            if not paths or not paths <= set(candidate.input_paths):
                raise ValueError("Supplied-intermediate coverage must name actual task inputs")
        elif paths:
            raise ValueError("Only results and supplied inputs name coverage artifact paths")
        if (item.role == "redundant") != (item.counterpart_id is not None):
            raise ValueError("Redundancy requires an explicit retained source-call counterpart")
    if set(uses) != set(known):
        raise ValueError(
            "Missing original source-call accounting: " + ", ".join(sorted(set(known) - set(uses)))
        )
    if known and outputs != set(candidate.output_paths):
        raise ValueError("Every requested output needs original-source result provenance")
    for identity, item in uses.items():
        if item.role != "redundant":
            continue
        seen = {identity}
        current = identity
        while uses[current].role == "redundant":
            other = uses[current].counterpart_id
            if other not in known or other in seen:
                raise ValueError("Redundancy counterpart is absent or cyclic")
            if known[current]["function"] != known[other]["function"]:
                raise ValueError(
                    "Different source operations cannot be claimed as redundant counterparts"
                )
            seen.add(other)
            current = other
        if uses[current].role not in {"result", "supplied_input"}:
            raise ValueError(
                "A redundant result must resolve to an actual retained result or supplied input"
            )
