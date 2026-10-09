"""Check a specification worker's output shape and source binding, not its science."""

import json
import math
from pathlib import Path, PurePosixPath


def proposal_action(workspace: Path) -> str:
    """A source-bound rejection ends the seed; specification permits construction."""
    proposal = json.loads((workspace / "proposal.json").read_text())
    seed = json.loads((workspace / "seed.json").read_text())
    if proposal.get("schema_version") != 1 or proposal.get("status") not in {
        "specified",
        "rejected",
    }:
        raise ValueError("Unsupported proposal")
    if proposal.get("source_sha256") != seed["source_sha256"]:
        raise ValueError("Proposal belongs to a different source")

    def text(record, key):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Proposal requires {key}")
        return value

    text(proposal, "rationale")
    paths = proposal.get("evidence_paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("Proposal requires source evidence paths")
    for value in paths:
        if not isinstance(value, str):
            raise ValueError("Invalid proposal evidence path")
        path = PurePosixPath(value)
        target = workspace / path
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in value
            or (not target.is_file() or not target.resolve().is_relative_to(workspace.resolve()))
        ):
            raise ValueError("Missing or unsafe proposal evidence")
    if proposal["status"] == "rejected":
        return "rejected"
    for key in ("objective", "reference_ecosystem", "validation_strategy", "runtime_rationale"):
        text(proposal, key)
    for key in ("methodology", "unresolved"):
        if (
            not isinstance(proposal.get(key), list)
            or any(not isinstance(value, str) or not value.strip() for value in proposal[key])
            or (key == "methodology" and not proposal[key])
        ):
            raise ValueError(f"Proposal requires {key}")
    for key, fields in (
        ("inputs", ("path", "identity", "origin", "preparation")),
        ("deliverables", ("path", "description")),
    ):
        values = proposal.get(key)
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, dict) for value in values)
        ):
            raise ValueError(f"Proposal requires {key}")
        for value in values:
            for field in fields:
                text(value, field)
            if key == "deliverables" and not PurePosixPath(value["path"]).is_absolute():
                raise ValueError("Deliverable requires absolute solver path")
    subgoals = proposal.get("subgoals")
    if not isinstance(subgoals, list) or not 2 <= len(subgoals) <= 4:
        raise ValueError("Proposal requires two to four subgoals")
    seen = set()
    total = 0.0
    for subgoal in subgoals:
        if not isinstance(subgoal, dict):
            raise ValueError("Invalid scientific subgoal")
        identity = text(subgoal, "id")
        text(subgoal, "description")
        weight = subgoal.get("weight")
        dependencies = subgoal.get("depends_on")
        if identity in seen or type(weight) not in (int, float) or not 0 < weight <= 1:
            raise ValueError("Invalid subgoal identity or weight")
        if not isinstance(dependencies, list) or any(
            not isinstance(value, str) or value not in seen for value in dependencies
        ):
            raise ValueError("Dependencies must name earlier scientific subgoals")
        total += weight
        seen.add(identity)
    if not math.isclose(total, 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Scientific weights must sum to one")
    return "construction"
