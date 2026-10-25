"""Drain durable stage evidence immediately; poll uncertain work conservatively."""

from pathlib import Path

from biotasks.validation.journal import STAGES


def waiting(directory: Path, state: str, stages: tuple[str, ...] = STAGES) -> bool:
    parts = state.split(":", 2)
    if parts[0] in {"performed", "recovering"} and len(parts) == 2:
        stage = parts[1]
    elif state in stages:
        stage = state
    else:
        # Includes pending/unknown observations: never turn an uncertain handle
        # into a tight retry loop or change submission semantics.
        return True
    return stage not in stages or not (directory / (stage + ".json")).is_file()
