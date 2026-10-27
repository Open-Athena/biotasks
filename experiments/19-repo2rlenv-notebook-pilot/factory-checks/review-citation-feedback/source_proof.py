"""Bound citation diagnostics without changing schemas or acceptance predicates."""

import ast

GUIDANCE = """Return `findings` as a JSON array of objects, not a string containing JSON.
Copy each `path` literally from the `evidence_text` map and quote a literal
substring of its decoded value. Do not paraphrase, splice separate fragments or
insert ellipses. A new tool response is not automatically part of that map;
you can cite the proposal's exact unsupported claim and explain the missing
support. If validation names a finding/evidence index, correct that citation
without deleting a real blocker to obtain approval.
"""


def prove_prompt_only(before, after):
    text = after.decode()
    assert text.count(GUIDANCE) == 1
    assert text.replace(GUIDANCE, "", 1) == before.decode(), "Unknown review prompt change"


def prove_diagnostics_only(before, after):
    old, new = ast.parse(before), ast.parse(after)
    old_review = next(
        node
        for node in old.body
        if isinstance(node, ast.FunctionDef) and node.name == "validate_specification_review"
    )
    new_review = next(
        node
        for node in new.body
        if isinstance(node, ast.FunctionDef) and node.name == "validate_specification_review"
    )
    # Enumerating the same findings/citations adds only diagnostic indices.
    for target, names in [
        (new_review.body[2], ["finding_index", "finding"]),
        (new_review.body[2].body[0], ["evidence_index", "item"]),
    ]:
        assert isinstance(target, ast.For)
        assert isinstance(target.target, ast.Tuple)
        assert [node.id for node in target.target.elts] == names
        assert isinstance(target.iter, ast.Call)
        assert isinstance(target.iter.func, ast.Name) and target.iter.func.id == "enumerate"
        assert len(target.iter.args) == 1 and not target.iter.keywords
        target.target = ast.Name(id=names[1], ctx=ast.Store())
        target.iter = target.iter.args[0]
    citation = new_review.body[2].body[0]
    expected = ast.parse('location = f"findings[{finding_index}].evidence[{evidence_index}]"').body[
        0
    ]
    assert ast.dump(citation.body[0]) == ast.dump(expected)
    citation.body.pop(0)
    # Only the diagnostic arguments to the same two ValueErrors may differ.
    for function in [old_review, new_review]:
        errors = [node for node in ast.walk(function) if isinstance(node, ast.Raise)]
        assert len(errors) == 2
        for error in errors:
            assert error.cause is None
            call = error.exc
            assert isinstance(call, ast.Call)
            assert isinstance(call.func, ast.Name) and call.func.id == "ValueError"
            assert len(call.args) == 1 and not call.keywords
            call.args = [ast.Constant(value="citation diagnostic")]
    assert ast.dump(old) == ast.dump(new), (
        "Change outside citation diagnostics; schemas or acceptance predicates differ"
    )
