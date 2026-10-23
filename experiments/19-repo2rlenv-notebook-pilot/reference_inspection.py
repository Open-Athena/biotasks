"""Inspect recorded reference text without executing or editing scientific code."""

import hashlib
import json
import re
import time
from pathlib import PurePosixPath

from package_inspection import tool


def reference_catalog(outputs):
    catalog = {}
    for item in outputs:
        path = item["path"]
        relative = PurePosixPath(path)
        if (
            not path
            or path != relative.as_posix()
            or relative.is_absolute()
            or ".." in relative.parts
            or path in catalog
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            or type(item["bytes"]) is not int
            or item["bytes"] < 0
        ):
            raise ValueError("Invalid or ambiguous recorded reference identity")
        catalog[path] = {key: item[key] for key in ("sha256", "bytes")}
    return {
        "files": catalog,
        "boundary": (
            "Read-only UTF-8 text inspection of these recorded reference outputs only. "
            "Every read verifies the complete file hash and size before returning text. "
            "No execution, imports, filesystem writes, arbitrary paths or input-file access. "
            "Binary content remains an explicit inspection gap. Observed text establishes "
            "file contents, not scientific correctness or portable comparison tolerances. "
            "Text reads default to columns 1–1000 of each selected line; reported slices "
            "are incomplete fragments. Explicit larger windows or end_column:null are allowed. "
            "Reference values are private evidence, not material to copy into solver instructions."
        ),
    }


REFERENCE_TOOLS = [
    tool(
        "read_reference_file",
        "Read inclusive line and Unicode-character column ranges from a catalog reference artifact. Defaults to lines 1–200, columns 1–1000 per line. Slices and full line lengths are explicit; a fragment is not a complete document. Use other windows to inspect compact one-line files. Any positive range is allowed; end_column:null reads the complete remaining line. Returns the verified full file identity and total line count. Binary files cannot be read as text.",
        {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
            "start_column": {"type": "integer", "minimum": 1},
            "end_column": {"anyOf": [{"type": "integer", "minimum": 1}, {"type": "null"}]},
        },
        ["path"],
    )
]


class ReferenceInspection:
    def __init__(self, root, catalog, deadline):
        self.root, self.catalog, self.deadline = root, catalog, deadline

    def remaining(self):
        if time.time() >= self.deadline:
            raise TimeoutError("Reference inspection deadline exhausted")

    async def read_reference_file(
        self, path, start_line=1, end_line=200, start_column=1, end_column=1000
    ):
        if (
            path not in self.catalog
            or type(start_line) is not int
            or type(end_line) is not int
            or not 1 <= start_line <= end_line
            or type(start_column) is not int
            or start_column < 1
            or (
                end_column is not None
                and (type(end_column) is not int or end_column < start_column)
            )
        ):
            raise ValueError("Use a catalog path and inclusive positive line/column ranges")
        self.remaining()
        target = self.root
        for part in PurePosixPath(path).parts:
            target = target / part
            if target.is_symlink():
                raise ValueError("Reference symlinks are not inspection evidence")
        if not target.is_file() or not target.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("Recorded reference file is unavailable")
        hasher, count, total, lines = hashlib.sha256(), 0, 0, []
        line_characters, sliced_lines = {}, []
        # Return no content until the complete identity is verified. Nothing is
        # imported, unpickled, extracted or executed, even files named as code.
        with target.open("rb") as stream:
            for total, raw in enumerate(stream, 1):
                self.remaining()
                hasher.update(raw)
                count += len(raw)
                text = raw.decode("utf-8")
                if "\0" in text:
                    raise ValueError("Binary reference; no UTF-8 text inspection available")
                if start_line <= total <= end_line:
                    text = text.rstrip("\r\n")
                    line_characters[str(total)] = len(text)
                    fragment = text[start_column - 1 : end_column]
                    if fragment != text:
                        sliced_lines.append(total)
                    lines.append({"line": total, "text": fragment})
            identity = {"sha256": hasher.hexdigest(), "bytes": count}
            if identity != self.catalog[path]:
                raise ValueError("Reference identity differs from the executed record")
        return json.dumps(
            {
                "path": path,
                **identity,
                "total_lines": total,
                "start_line": start_line,
                "end_line": min(end_line, total),
                "start_column": start_column,
                "end_column": end_column,
                "line_characters": line_characters,
                "sliced_lines": sliced_lines,
                "lines": lines,
            }
        )

    @property
    def handlers(self):
        async def read(**kwargs):
            try:
                return await self.read_reference_file(**kwargs)
            except TimeoutError:
                raise
            except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
                return json.dumps(
                    {
                        "error": type(error).__name__,
                        "message": "Reference text unavailable for these arguments. Use only recorded paths and valid line ranges. Missing, changed, linked or binary artifacts remain evidence gaps; do not infer their contents.",
                    }
                )

        return {"read_reference_file": read}
