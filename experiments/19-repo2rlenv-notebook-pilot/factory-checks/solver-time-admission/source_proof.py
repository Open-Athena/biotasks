"""Permit only an earlier pre-dispatch refusal, preserving all existing limits."""

import ast


def prove_early_refusal_only(before, after):
    old, new = ast.parse(before), ast.parse(after)

    def trial(tree):
        klass = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "IrisDaytonaExecution"
        )
        return next(
            node
            for node in klass.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_trial"
        )

    previous, current = trial(old), trial(new)
    assignment = ast.parse('solving = agent not in {"nop", "oracle", "probe"}').body[0]
    guard = ast.parse(
        'if solving and timeout < self.solver_seconds:\n    raise TimeoutError("Insufficient allocation time for the solver allowance and cleanup")'
    ).body[0]
    early = ast.parse(
        'if timeout <= 0:\n    raise TimeoutError("Insufficient allocation time for trial and cleanup")'
    ).body[0]
    forwarding = ast.parse('kwargs["timeout_sec"] = timeout').body[0]
    locations = [i for i, node in enumerate(current.body) if ast.dump(node) == ast.dump(assignment)]
    assert len(locations) == 1
    index = locations[0]
    assert ast.dump(current.body[index - 1]) == ast.dump(early)
    assert ast.dump(current.body[index + 1]) == ast.dump(guard)
    assert ast.dump(current.body[index + 2]) == ast.dump(forwarding)
    del current.body[index : index + 2]
    old_locations = [
        i for i, node in enumerate(previous.body) if ast.dump(node) == ast.dump(assignment)
    ]
    assert len(old_locations) == 1
    del previous.body[old_locations[0]]
    assert ast.dump(old) == ast.dump(new), "Unknown change beyond the earlier solver-window refusal"
