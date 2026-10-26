"""Build a diagnostic-only candidate; leave the frozen scientific files intact."""

import ast
import difflib
from collections import Counter
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
PROTOCOL = EXPERIMENT / "grading_protocol.py"
PROMPT = EXPERIMENT.parents[1] / "src/biotasks/prompts/notebook-grader-review.md"
OLD = '        raise ValueError("Explicitly assess every supplied asset value hint exactly once")'
NEW = """        counts = Counter(observed)
        raise ValueError(
            "Explicitly assess every supplied asset value hint exactly once; "
            f"missing_hint_ids={sorted(expected - set(observed))}; "
            f"unexpected_hint_ids={sorted(set(observed) - expected)}; "
            f"duplicate_hint_ids={sorted(key for key, count in counts.items() if count > 1)}. "
            "Use the recorded hint IDs verbatim. Correct the coverage without "
            "changing scientific assessments to satisfy validation."
        )"""
PROMPT_GUIDANCE = """
Return nested objects and arrays as actual JSON objects and arrays, never as
JSON-encoded strings. On artifact-validation feedback, correct the named schema
or identity defect while preserving all other supported assessments. Hint IDs
are opaque recorded identities: copy them verbatim, and use the feedback's
missing, unexpected and duplicate ID lists to locate a coverage error. Do not
invent an assessment, mark an unresolved hint unrelated, or change a scientific
conclusion merely to obtain schema acceptance.

"""


def protocol_candidate(source):
    assert source.count(OLD) == 1, "Reassess candidate against changed source"
    return source.replace(OLD, NEW)


def checker(source):
    """Compile only the existing pure validation function for offline comparisons."""
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "check_review_asset_hints"
    )
    namespace = {"Counter": Counter}
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), "<hint-coverage>", "exec"), namespace
    )
    return namespace[function.name]


def proposed_changes():
    source = PROTOCOL.read_text()
    prompt = PROMPT.read_text()
    # Keep the opening orientation followed by this explicit tool-output rule.
    first_break = prompt.index("\n\n") + 2
    return {
        PROTOCOL: (source, protocol_candidate(source)),
        PROMPT: (prompt, prompt[:first_break] + PROMPT_GUIDANCE.lstrip() + prompt[first_break:]),
    }


def patch():
    repo = EXPERIMENT.parents[1]
    return "".join(
        "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="a/" + str(path.relative_to(repo)),
                tofile="b/" + str(path.relative_to(repo)),
            )
        )
        for path, (before, after) in proposed_changes().items()
    )


if __name__ == "__main__":
    print(patch(), end="")
