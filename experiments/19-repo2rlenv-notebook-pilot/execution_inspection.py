"""Read-only, identity-bound observations; never promote them to acceptance controls."""

import hashlib
import json
import re
import time
from pathlib import PurePosixPath

from package_inspection import tool

EXECUTION_TOOLS = [
    tool(
        "search_execution_evidence",
        "Search literal text in recorded commands and outputs. These are prior observations, not extra fresh acceptance controls. Results are paginated; an absent match only concerns this catalog.",
        {
            "query": {"type": "string"},
            "start_match": {"type": "integer", "minimum": 1},
            "end_match": {"type": "integer", "minimum": 1},
        },
        ["query"],
    ),
    tool(
        "read_execution_evidence",
        "Read a catalog operation's command, raw output, decoded stdout/stderr or process receipt. Default lines1-200/columns1-1000; positive windows are allowed, end_column:null reads the remaining line. Full original file identities are checked on every read. Decoded output is an observation, not proof of scientific validity.",
        {
            "operation_id": {"type": "string"},
            "section": {
                "type": "string",
                "enum": ["command", "output", "stdout", "stderr", "process"],
            },
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
            "start_column": {"type": "integer", "minimum": 1},
            "end_column": {"anyOf": [{"type": "integer", "minimum": 1}, {"type": "null"}]},
        },
        ["operation_id", "section"],
    ),
]


class ExecutionInspection:
    def __init__(self, roots, deadline):
        self.roots, self.deadline, self.catalog = roots, deadline, {}
        for alias, root in roots.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]*", alias) or root.is_symlink():
                raise ValueError("Use controller-selected regular evidence roots")
            operations = root / "operations"
            if not operations.exists():
                continue
            if operations.is_symlink():
                raise ValueError("Linked operation evidence is forbidden")
            for directory in sorted(operations.iterdir()):
                self.remaining()
                if (
                    directory.is_symlink()
                    or not directory.is_dir()
                    or not re.fullmatch(r"[0-9]+", directory.name)
                ):
                    raise ValueError("Invalid operation evidence directory")
                operation, identity = self.load(root, f"operations/{directory.name}/operation.json")
                row = {"operation": identity, "available": False}
                process = operation.get("process", {})
                output_path = f"operations/{directory.name}/output.log"
                if operation.get("state") == "returned" and (root / output_path).exists():
                    output, output_identity = self.load(root, output_path, decode=False)
                    if (
                        not isinstance(process, dict)
                        or not isinstance(operation.get("argv"), list)
                        or not operation["argv"]
                        or any(not isinstance(arg, str) for arg in operation["argv"])
                        or not isinstance(operation.get("remote_label"), str)
                        or not operation["remote_label"]
                        or type(operation.get("seconds")) is not int
                        or operation["seconds"] < 1
                        or process.get("argv") != operation.get("argv")
                        or process.get("label") != operation.get("remote_label")
                        or process.get("timeout_seconds") != operation.get("seconds")
                        or type(process.get("exit_code")) is not int
                        or type(process.get("timed_out")) is not bool
                        or process.get("log_sha256") != output_identity["sha256"]
                    ):
                        raise ValueError("Operation output is not bound to its completion receipt")
                    row.update(
                        output=output_identity,
                        exit_code=process["exit_code"],
                        timed_out=process["timed_out"],
                    )
                    try:
                        output.decode("utf-8")
                    except UnicodeError:
                        row["gap"] = "Recorded binary output; text inspection unavailable."
                    else:
                        row["available"] = True
                else:
                    row["gap"] = "No verified returned completion/log; execution is not disproved."
                self.catalog[f"{alias}/{directory.name}"] = row

    def remaining(self):
        if time.time() >= self.deadline:
            raise TimeoutError("Execution inspection deadline exhausted")

    def load(self, root, path, *, decode=True, expected=None):
        self.remaining()
        if root.is_symlink():
            raise ValueError("Linked execution evidence root is forbidden")
        target = root
        for part in PurePosixPath(path).parts:
            target = target / part
            if target.is_symlink():
                raise ValueError("Linked execution evidence is forbidden")
        if not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError("Recorded execution evidence is unavailable")
        raw = target.read_bytes()
        self.remaining()
        identity = {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if expected is not None and identity != expected:
            raise ValueError("Execution evidence changed after cataloging")
        return (json.loads(raw) if decode else raw), identity

    def sections(self, operation_id):
        self.remaining()
        row = self.catalog[operation_id]
        if not row["available"]:
            raise ValueError("This operation remains an explicit evidence gap")
        root = self.roots[operation_id.split("/", 1)[0]]
        operation, _ = self.load(root, row["operation"]["path"], expected=row["operation"])
        raw, _ = self.load(root, row["output"]["path"], decode=False, expected=row["output"])
        text = raw.decode("utf-8")
        # Some controller helpers return JSON containing captured shell output.
        # Decode it for inspection only; its content never supplies a reward.
        try:
            payload = json.loads(text)
        except ValueError:
            payload = None
        decoded = (
            isinstance(payload, dict)
            and isinstance(payload.get("stdout"), str)
            and isinstance(payload.get("stderr", ""), str)
        )
        return {
            "command": json.dumps(operation["argv"], ensure_ascii=False, indent=2),
            "process": json.dumps(operation["process"], ensure_ascii=False, indent=2),
            "output": text,
            "stdout": payload["stdout"] if decoded else text,
            "stderr": payload.get("stderr", "") if decoded else "",
        }, {
            "operation_id": operation_id,
            **row,
            "output_json_decoded": decoded,
            "decoded_output_metadata": {
                key: value for key, value in payload.items() if key not in {"stdout", "stderr"}
            }
            if decoded
            else None,
        }

    async def read_execution_evidence(
        self, operation_id, section, start_line=1, end_line=200, start_column=1, end_column=1000
    ):
        if (
            type(start_line) is not int
            or type(end_line) is not int
            or not 1 <= start_line <= end_line
            or type(start_column) is not int
            or start_column < 1
            or (
                end_column is not None
                and (type(end_column) is not int or end_column < start_column)
            )
        ):
            raise ValueError("Use inclusive positive line/column ranges")
        sections, identity = self.sections(operation_id)
        lines = sections[section].splitlines()
        return json.dumps(
            {
                **identity,
                "section": section,
                "total_lines": len(lines),
                "lines": [
                    {
                        "line": i + 1,
                        "text": line[start_column - 1 : end_column],
                        "full_line_characters": len(line),
                    }
                    for i, line in enumerate(lines)
                    if start_line <= i + 1 <= end_line
                ],
                "start_column": start_column,
                "end_column": end_column,
            }
        )

    async def search_execution_evidence(self, query, start_match=1, end_match=20):
        self.remaining()
        if (
            not isinstance(query, str)
            or not query
            or type(start_match) is not int
            or type(end_match) is not int
            or not 1 <= start_match <= end_match
        ):
            raise ValueError("Use literal nonempty text and positive result ranges")
        total, matches = 0, []
        for operation_id, row in self.catalog.items():
            if not row["available"]:
                continue
            sections, identity = self.sections(operation_id)
            for section, text in sections.items():
                for i, line in enumerate(text.splitlines(), 1):
                    self.remaining()
                    column = line.find(query)
                    if column < 0:
                        continue
                    total += 1
                    if start_match <= total <= end_match:
                        matches.append(
                            {
                                "operation_id": operation_id,
                                "section": section,
                                "line": i,
                                "match_column": column + 1,
                                "text": line[column : column + 1000],
                                "source_identities": {
                                    k: identity[k] for k in ("operation", "output")
                                },
                            }
                        )
        return json.dumps(
            {
                "total_matching_lines": total,
                "matches": matches,
                "scope": "This catalog only; not a complete acceptance-control inventory.",
            }
        )

    @property
    def handlers(self):
        def guarded(method):
            async def read(**kwargs):
                try:
                    return await method(**kwargs)
                except TimeoutError:
                    raise
                except (ValueError, KeyError, TypeError, OSError, UnicodeError):
                    return json.dumps(
                        {
                            "error": "Execution evidence unavailable or changed",
                            "scope": "Do not infer that the claimed experiment never ran.",
                        }
                    )

            return read

        return {
            name: guarded(getattr(self, name))
            for name in ("read_execution_evidence", "search_execution_evidence")
        }
