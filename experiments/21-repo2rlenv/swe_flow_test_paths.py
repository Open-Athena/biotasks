"""Explicit SWE-flow adaptation: identify callers using configured test paths.

Executed only in the approved remote worker. Original and adapted driver bytes
are preserved before invoking the otherwise unchanged native worker module.
"""

import hashlib
import json
import runpy
import sys
from importlib.resources import files
from pathlib import Path

NATIVE_CONDITION = 'elif frame.f_back and "/tests/" in frame.f_back.f_code.co_filename:'


def adapt_driver(source, test_paths):
    if source.count(NATIVE_CONDITION) != 1:
        raise ValueError("Pinned tracer condition changed")
    roots = []
    for relative in test_paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Test paths must remain within the workspace")
        roots.append(str(Path("/workspace") / path))
    if not roots:
        raise ValueError("No configured test paths")
    condition = (
        "elif frame.f_back and any("
        "Path(frame.f_back.f_code.co_filename) == Path(root) or "
        "Path(root) in Path(frame.f_back.f_code.co_filename).parents "
        f"for root in {roots!r}):"
    )
    return source.replace(NATIVE_CONDITION, condition)


def main():
    config, destination = map(Path, sys.argv[1:])
    settings = json.loads(config.read_text())
    driver = Path(str(files("repo2rlenv.pipelines.recipes.swe_flow").joinpath("trace_driver.py")))
    original = driver.read_bytes()
    adapted = adapt_driver(original.decode(), settings["options"]["test_paths"]).encode()
    evidence = destination.parent / "trace-path-adaptation"
    evidence.mkdir(exist_ok=False)
    (evidence / "original.py").write_bytes(original)
    (evidence / "adapted.py").write_bytes(adapted)
    (evidence / "manifest.json").write_text(
        json.dumps(
            {
                "adaptation": "configured_test_caller_paths",
                "test_paths": settings["options"]["test_paths"],
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "adapted_sha256": hashlib.sha256(adapted).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    driver.write_bytes(adapted)
    runpy.run_module("repo2rlenv.pipelines.recipes.swe_flow.worker", run_name="__main__")


if __name__ == "__main__":
    main()
