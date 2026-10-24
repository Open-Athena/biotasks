"""Experimental generic recipe policy; no repository/package-specific branches.

Only literal apt-get install, update, or update && install forms are supported.
Other commands are preserved. Ambiguous literal APT commands are unsupported;
this is deliberately not a shell parser, dependency inference or action replay.
"""

import re
import shlex
from contextlib import contextmanager
from copy import deepcopy

POLICY = "apt-index-refresh-v1"
MARKER = "# BioTasks experimental emitter policy: " + POLICY + "\n"
OPTIONS = {"-y", "--yes", "--assume-yes", "--no-install-recommends", "--no-install-suggests"}
QUIET = {"-q", "-qq", "--quiet"}
PACKAGE = re.compile(r"[a-z0-9][a-z0-9+.:_~=-]*\Z")
APT = re.compile(r"(?<![\w-])(?:apt-get|apt)(?![\w-])")


class UnsupportedRecipe(ValueError):
    pass


def words(command):
    if any(c in command for c in ";&|<>()$`\\\n\r#"):
        raise UnsupportedRecipe("APT command has unsupported shell syntax")
    try:
        return shlex.split(command)
    except ValueError as error:
        raise UnsupportedRecipe("APT command has invalid quoting") from error


def install(command):
    tokens = words(command)
    if tokens[:2] != ["apt-get", "install"]:
        raise UnsupportedRecipe("Only a literal apt-get install form is supported")
    packages = 0
    for token in tokens[2:]:
        if token in OPTIONS | QUIET:
            continue
        if not PACKAGE.fullmatch(token):
            raise UnsupportedRecipe("Unsupported APT install option/package expression")
        packages += 1
    if not packages:
        raise UnsupportedRecipe("APT install has no literal packages")


def update(command):
    tokens = words(command)
    if tokens[:2] != ["apt-get", "update"] or any(t not in QUIET for t in tokens[2:]):
        raise UnsupportedRecipe("Only a literal apt-get update form is supported")


def normalize(command):
    if not isinstance(command, str) or not command.strip():
        raise UnsupportedRecipe("Rebuild command must be nonempty text")
    if not APT.search(command):
        return command
    parts = command.split("&&")
    if len(parts) == 2:
        update(parts[0])
        install(parts[1])
        return command
    if len(parts) != 1:
        raise UnsupportedRecipe("Unsupported APT command chain")
    tokens = words(command)
    if tokens[:2] == ["apt-get", "update"]:
        update(command)
        return command
    install(command)
    return "apt-get update && " + command


@contextmanager
def emitter(native):
    """Temporarily wrap one verified emitter; never changes native source files."""
    original = native._build_clean_recipe
    changes = []

    def render(owner, name, data):
        candidate = deepcopy(data)
        before = data.get("rebuild_cmds") or []
        after = [normalize(c) for c in before]
        candidate["rebuild_cmds"] = after
        rendered = original(owner, name, candidate)
        different = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
        if different and rendered is not None:
            changes.append({"repo": owner + "/" + name, "commands": different})
            return MARKER + rendered
        return rendered

    native._build_clean_recipe = render
    try:
        yield changes
    finally:
        native._build_clean_recipe = original
