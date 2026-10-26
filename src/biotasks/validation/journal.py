"""One effect per transition, with durable intent and independently verified evidence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from biotasks.validation.files import json_sha, lock, read_json, require, sha, write_json

STAGES = (
    "candidate_verified",
    "submission_recorded",
    "remote_terminal",
    "archive_readback_verified",
    "publication_resolved",
    "cleanup_terminal",
    "cleanup_verified",
)


@dataclass(frozen=True)
class Binding:
    path: str
    sha256: str

    def verify(self) -> None:
        file = Path(self.path)
        require(file.is_file() and not file.is_symlink(), f"Evidence missing: {file}")
        require(sha(file) == self.sha256, f"Evidence changed: {file}")

    def json(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class Observation:
    state: Literal["ready", "pending", "absent", "held"]
    evidence: tuple[Binding, ...] = ()
    reason: str | None = None


class Adapter(Protocol):
    def probe(self, stage: str) -> Observation: ...
    def verify(self, stage: str, evidence: tuple[Binding, ...], /) -> None: ...
    def perform(self, stage: str) -> None: ...
    def recover(self, stage: str) -> None: ...


def advance(
    run_id: str,
    inputs: tuple[Binding, ...],
    path: Path,
    adapter: Adapter,
    stages: tuple[str, ...] = STAGES,
) -> str:
    """Never repeat an uncertain effect; recover its existing identity instead.

    Adapters may repeat only idempotent recovery actions. In particular a missing
    remote handle after submission intent is *pending*, not permission to submit.
    A held state retains evidence/resources and is never a successful completion.
    """
    require(bool(run_id) and bool(inputs), "A run needs an identity and bound inputs")
    require(bool(stages) and all(stages) and len(set(stages)) == len(stages), "Invalid stages")
    plan = {"run_id": run_id, "inputs": [item.json() for item in inputs], "stages": stages}
    with lock(path.with_suffix(path.suffix + ".lock")):
        journal: dict[str, Any]
        for item in inputs:
            item.verify()
        if path.exists():
            journal = read_json(path)
            require(journal["plan_sha256"] == json_sha(plan), "Plan changed; use a new run")
        else:
            journal = {
                "schema_version": 1,
                "plan_sha256": json_sha(plan),
                "run_id": run_id,
                "stages": [],
                "events": [],
            }
            write_json(path, journal)
        require(len(journal["stages"]) <= len(stages), "Journal has too many stages")
        for index, record in enumerate(journal["stages"]):
            require(record["stage"] == stages[index], "Noncontiguous journal")
            evidence = tuple(Binding(**item) for item in record["evidence"])
            require(bool(evidence), "A stage needs durable evidence")
            for item in evidence:
                item.verify()
            adapter.verify(record["stage"], evidence)
        if len(journal["stages"]) == len(stages):
            return "complete"
        stage = stages[len(journal["stages"])]
        observed = adapter.probe(stage)
        if observed.state == "ready":
            require(bool(observed.evidence), "Stage has no durable evidence")
            for item in observed.evidence:
                item.verify()
            adapter.verify(stage, observed.evidence)
            journal["stages"].append(
                {"stage": stage, "evidence": [item.json() for item in observed.evidence]}
            )
            journal.pop("intent", None)
            journal["events"].append({"stage": stage, "event": "evidence_verified"})
            write_json(path, journal)
            return stage
        if observed.state in ("pending", "held"):
            return f"{observed.state}:{stage}:{observed.reason or ''}"
        require(observed.state == "absent", "Unknown observation state")
        if journal.get("intent"):
            require(journal["intent"]["stage"] == stage, "Intent stage mismatch")
            adapter.recover(stage)
            return "recovering:" + stage
        journal["intent"] = {"stage": stage, "run_id": run_id}
        journal["events"].append({"stage": stage, "event": "intent_persisted"})
        write_json(path, journal)
        adapter.perform(stage)
        return "performed:" + stage
