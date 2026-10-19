"""Assess original retained JSON with the pinned native static draft validator.

Only JSON/schema checks and Python AST parsing occur. Generated code is never
executed, edited, emitted or supplied back to an author.
"""

import argparse
import ast
import hashlib
import inspect
import json
import tarfile
from pathlib import Path

from repo2rlenv.pipelines.recipes.terminal.draft import TerminalDraft


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert digest(args.source_archive) == "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
    validator_path = Path(inspect.getfile(TerminalDraft))
    with tarfile.open(args.source_archive, "r|gz") as archive:
        source = next(m for m in archive if m.name.endswith("/src/repo2rlenv/pipelines/recipes/terminal/draft.py"))
        assert archive.extractfile(source).read() == validator_path.read_bytes()
    rows = []
    for path in sorted(args.responses.glob("*.json")):
        response = json.loads(path.read_text())
        if not response.get("choices"):
            continue
        content = response["choices"][0]["message"]["content"]
        value = json.loads(content)
        row = {
            "response_file": path.name,
            "response_sha256": digest(path),
            "answer_json_object": isinstance(value, dict),
            "generated_code_executed": False,
            "task_edited": False,
            "new_model_calls": 0,
            "text_fields": {name: {"characters": len(value.get(name, "")), "actual_newlines": value.get(name, "").count("\n")} for name in ("instruction", "tests_python", "solution_shell")},
        }
        try:
            ast.parse(value["tests_python"])
            row["tests_python_AST_parse"] = "passed"
        except SyntaxError as exc:
            row.update(tests_python_AST_parse="failed", syntax_error_message=exc.msg, syntax_error_line=exc.lineno)
        try:
            TerminalDraft.model_validate(value)
            row["native_TerminalDraft_schema"] = "passed"
        except Exception as exc:
            row.update(native_TerminalDraft_schema="failed", native_error_type=type(exc).__name__)
            if hasattr(exc, "errors"):
                row["native_errors"] = [{"loc": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in exc.errors(include_input=False, include_context=False, include_url=False)]
            elif isinstance(exc, SyntaxError):
                row.update(native_syntax_error_message=exc.msg, native_syntax_error_line=exc.lineno)
        rows.append(row)
    assert len(rows) == 2
    report = {
        "stage": "post_run_static_assessment_of_original_retained_completions",
        "native_validator_sha256": digest(validator_path),
        "native_validator_matches_pinned_source_archive": True,
        "rows": rows,
        "new_model_calls": 0,
        "task_fixes": 0,
        "generated_code_executed": False,
        "limits": [
            "Schema/AST checks do not establish task correctness, a native export, or a completed repair loop.",
            "Original callers timed out; these retained responses are assessed separately and never replayed into generation.",
            "An invalid first answer does not establish what unexecuted native automatic repairs would have produced.",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"responses_assessed": len(rows), "native_schema_passed": sum(r["native_TerminalDraft_schema"] == "passed" for r in rows), "new_models": 0, "task_changes": 0}))


if __name__ == "__main__":
    main()
