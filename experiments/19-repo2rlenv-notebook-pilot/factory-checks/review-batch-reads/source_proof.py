"""Preserve the original packet reader and restrict the batching extension."""

import ast

GUIDANCE = """Use `read_review_evidence_batch` when several field/pointer lookups are already
known. Its `requests` array contains ordinary single-read argument objects and
returns one result per request in the same order. Batch independent lookups to
avoid a model round trip for each item; use a keys read first when navigation
is needed. Every item retains its identity checks and the existing deadline;
an unavailable item remains a gap, never approval or an extra control.
"""


def prove_prompt_only(before, after):
    text = after.decode()
    assert text.count(GUIDANCE) == 1
    assert text.replace(GUIDANCE, "", 1) == before.decode()


def prove_readonly_extension(before, after):
    old, new = ast.parse(before), ast.parse(after)
    original_doc = old.body[0].value.value
    assert new.body[0].value.value == original_doc.replace(
        "through one read-only structured tool", "through read-only structured tools"
    )
    new.body[0] = old.body[0]
    old_class = next(
        node for node in old.body if isinstance(node, ast.ClassDef) and node.name == "ReviewPacket"
    )
    new_class = next(
        node for node in new.body if isinstance(node, ast.ClassDef) and node.name == "ReviewPacket"
    )
    previous = {
        node.name: node
        for node in old_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    current = {
        node.name: node
        for node in new_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert set(previous) == set(current)
    tools = current["tools"]
    assert len(tools.body) == 3
    assert ast.dump(tools.body[0]) == ast.dump(previous["tools"].body[0])
    single = tools.body[1]
    assert isinstance(single, ast.Assign) and len(single.targets) == 1
    assert isinstance(single.targets[0], ast.Name) and single.targets[0].id == "single"
    assert ast.dump(single.value) == ast.dump(previous["tools"].body[1].value.elts[0])
    result = tools.body[2].value
    assert isinstance(result, ast.List) and len(result.elts) == 2
    assert isinstance(result.elts[0], ast.Name) and result.elts[0].id == "single"
    addition = result.elts[1]
    assert isinstance(addition, ast.Call) and len(addition.args) == 4 and not addition.keywords
    assert isinstance(addition.args[1], ast.Constant) and isinstance(addition.args[1].value, str)
    addition.args[1] = ast.Constant(value="batch description")
    expected = (
        ast.parse(
            'tool("read_review_evidence_batch", "batch description", {"requests": {"type": "array", "minItems": 1, "items": single["function"]["parameters"]}}, ["requests"])'
        )
        .body[0]
        .value
    )
    assert ast.dump(addition) == ast.dump(expected)
    tools.body = previous["tools"].body
    handlers = current["handlers"]
    assert len(handlers.body) == 3
    assert ast.dump(handlers.body[0]) == ast.dump(previous["handlers"].body[0])
    batch = handlers.body[1]
    assert isinstance(batch, ast.AsyncFunctionDef) and batch.name == "batch"
    assert [arg.arg for arg in batch.args.args] == ["requests"]
    reads = 0
    for node in ast.walk(batch):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id in {"isinstance", "read"}
                reads += node.func.id == "read"
            else:
                assert ast.unparse(node.func) in {
                    "self.remaining",
                    "json.dumps",
                    "json.loads",
                    "results.append",
                }
        if isinstance(node, ast.expr) and isinstance(getattr(node, "ctx", None), ast.Store):
            assert isinstance(node, ast.Name) and node.id in {"results", "request", "response"}
        assert not isinstance(
            node, (ast.Import, ast.ImportFrom, ast.Lambda, ast.Yield, ast.YieldFrom)
        )
    assert reads == 1
    expected_return = (
        ast.parse('{"read_review_evidence": read, "read_review_evidence_batch": batch}')
        .body[0]
        .value
    )
    assert ast.dump(handlers.body[2].value) == ast.dump(expected_return)
    handlers.body = previous["handlers"].body
    assert ast.dump(old) == ast.dump(new), (
        "Original packet identity, read, reconstruction or other code changed"
    )
