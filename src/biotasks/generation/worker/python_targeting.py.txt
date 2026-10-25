"""Opt-in generic adapter for newly appended pytest targets.

The pinned native checkout is /workspace. No test/cwd/import/install/grading
changes. Existing recognized targets and non-pytest commands are preserved.
"""

import re
import shlex
from pathlib import PurePosixPath


def recognized_target(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    tokens = list(lexer)
    index = next(
        (i for i, token in enumerate(tokens) if token == "pytest" or token.endswith("/pytest")), -1
    )
    if index < 0:
        return False
    for token in tokens[index + 1 :]:
        if token in {";", "&&", "||", "|", "&", "(", ")"}:
            break
        if not token.startswith("-") and (
            token.split("::", 1)[0].endswith(".py") or "/" in token or token == "."
        ):
            return True
    return False


def wrap(original, checkout="/workspace"):
    root = PurePosixPath(checkout)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("Expected fixed absolute checkout")

    def targeted(commands, test_files):
        output = []
        for command in commands:
            if not re.search(r"\bpytest\b", command):
                output.extend(original([command], test_files))
                continue
            absolute = []
            for name in test_files:
                if not isinstance(name, str) or "\0" in name:
                    raise ValueError("Invalid repository test path")
                if not name.endswith(".py"):
                    continue
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Test path escapes checkout")
                absolute.append(str(root / path))
            if not absolute or recognized_target(command):
                output.append(command)
                continue
            # Reuse upstream's runner/target selection, then quote only its
            # exactly identified new suffix. Unexpected source behavior holds.
            inherited = original([command], absolute)
            expected = command.rstrip() + " " + " ".join(absolute)
            if inherited == [command]:
                output.append(command)
            elif inherited == [expected]:
                output.append(command.rstrip() + " " + shlex.join(absolute))
            else:
                raise ValueError("Unexpected pinned targeter behavior")
        return output

    return targeted
