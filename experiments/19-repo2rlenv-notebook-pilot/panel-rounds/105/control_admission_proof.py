"""Verify that scientific verdicts stay unchanged around shorter control admission."""

import ast

BEFORE_PROBE = """save_record(folder / "request.json", request)
await self.remote.upload(folder / "request.json", "/work/grading-private/request.json")
reply = await self.helper(["probe-check"], self.config["verifier_seconds"] + 10, "probe-preflight-" + str(self.probe_validation_number))
"""
AFTER_PROBE = """reply = await self.control_request(folder, request, operation="probe-check", label="probe-preflight-" + str(self.probe_validation_number))"""
BEFORE_CASE = """save_record(folder / "request.json", request)
await self.remote.upload(folder / "request.json", "/work/grading-private/request.json")
reply = await self.helper(["case"], self.config["verifier_seconds"] * (2 if probe else 1) + 10, "grading-control-" + str(self.case_number))
"""
AFTER_CASE = """reply = await self.control_request(folder, request, operation="case", label="grading-control-" + str(self.case_number), phases=2 if probe else 1)"""


def prove_control_admission_only(before, after):
    old, new = ast.parse(before), ast.parse(after)
    old_class = next(
        node
        for node in old.body
        if isinstance(node, ast.ClassDef) and node.name == "GradingSession"
    )
    new_class = next(
        node
        for node in new.body
        if isinstance(node, ast.ClassDef) and node.name == "GradingSession"
    )
    for name, previous, replacement in (
        ("validate_probe_execution", BEFORE_PROBE, AFTER_PROBE),
        ("case", BEFORE_CASE, AFTER_CASE),
    ):
        function = next(
            node
            for node in old_class.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == name
        )
        pattern = ast.parse(previous).body
        positions = [
            start
            for start in range(len(function.body) - len(pattern) + 1)
            if [ast.dump(node) for node in function.body[start : start + len(pattern)]]
            == [ast.dump(node) for node in pattern]
        ]
        assert len(positions) == 1
        start = positions[0]
        function.body[start : start + len(pattern)] = ast.parse(replacement).body
    additions = [
        node
        for node in new_class.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "control_request"
    ]
    assert len(additions) == 1
    old_class.body.insert(new_class.body.index(additions[0]), additions[0])
    assert ast.dump(old) == ast.dump(new), (
        "Change outside tested control admission; scientific acceptance or another method differs"
    )
