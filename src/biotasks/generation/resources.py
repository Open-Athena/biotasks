"""Installed code and frozen controller assets, independent of a checkout."""

from importlib.resources import files
from types import ModuleType
from typing import Any

from biotasks.validation.files import content_sha, json_sha


def code_files() -> dict[str, bytes]:
    root = files("biotasks.generation")
    result = {
        entry.name: entry.read_bytes()
        for entry in root.iterdir()
        if entry.is_file() and entry.name.endswith((".py", ".json"))
    }
    result.update(
        {
            "worker/" + entry.name: entry.read_bytes()
            for entry in (root / "worker").iterdir()
            if entry.is_file() and entry.name.endswith(".txt")
        }
    )
    return result


def code_identity() -> str:
    from biotasks.retention.actor import implementation

    return json_sha(
        {
            "generation": {name: content_sha(raw) for name, raw in code_files().items()},
            "retention": implementation(),
        }
    )


def assets() -> dict[str, bytes]:
    return {
        name.removeprefix("worker/").removesuffix(".txt"): raw
        for name, raw in code_files().items()
        if name.startswith("worker/")
    }


def cost_policy() -> Any:
    """Load the frozen original guard without creating bytecode in payloads."""
    module = ModuleType("biotasks_original_cost_guard")
    exec(compile(assets()["cost_guard.py"], "bundled:cost_guard.py", "exec"), module.__dict__)
    return module


def option_policy() -> Any:
    """Load the one canonical native-option guard for host and worker."""
    module = ModuleType("biotasks_native_option_policy")
    exec(compile(assets()["option_policy.py"], "bundled:option_policy.py", "exec"), module.__dict__)
    return module
