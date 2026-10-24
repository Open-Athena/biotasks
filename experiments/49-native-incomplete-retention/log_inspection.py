"""Review exact source-bound native text logs; preserve original archive bytes."""

import hashlib
import re
from contextlib import contextmanager

from biotasks.validation import preservation
from biotasks.validation.files import require


def log_path(task, name):
    pattern = (
        r"jobs/"
        + re.escape(task)
        + r"-(?:nop|oracle)/"
        + re.escape(task)
        + r"__[A-Za-z0-9_-]+/verifier/"
        + r"(?:test-stdout\.txt|test_output\.log)"
    )
    return re.fullmatch(pattern, name) is not None


def review(task, name, raw):
    require(log_path(task, name), "Unknown NUL-bearing artifact path")
    require(len(raw) <= 2 * 1024**2 and 0 < raw.count(b"\0") <= 1024**2, "Native log bounds")
    # This view exists only for inspection. The caller retains original bytes.
    view = raw.replace(b"\0", b"")
    preservation.inspect(view, name)
    require(
        all(value >= 32 or value in (9, 10, 13, 27) for value in view),
        "Non-text control bytes in native log",
    )
    return {
        "path": name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "nul_bytes": raw.count(b"\0"),
        "review": "Source-bound UTF-8 native verifier text with NUL padding; original bytes retained, scientific status unaccepted",
    }


@contextmanager
def reviewed_native_logs(task, approvals):
    require(0 < len(approvals) <= 4, "Native log exception count")
    expected = {r["path"]: r for r in approvals}
    require(len(expected) == len(approvals), "Duplicate native log exception")
    require(all(log_path(task, name) for name in expected), "Non-native exception path")
    original = preservation.inspect

    def inspect(raw, name, depth=0):
        if name in expected and b"\0" in raw:
            row = expected[name]
            require(
                len(raw) == row["bytes"] <= 2 * 1024**2
                and hashlib.sha256(raw).hexdigest() == row["sha256"]
                and 0 < raw.count(b"\0") == row["nul_bytes"] <= 1024**2,
                "Reviewed native log bytes changed",
            )
            view = raw.replace(b"\0", b"")
            require(
                all(value >= 32 or value in (9, 10, 13, 27) for value in view),
                "Non-text control bytes in native log",
            )
            return original(view, name, depth)
        return original(raw, name, depth)

    preservation.inspect = inspect
    try:
        yield
    finally:
        preservation.inspect = original
