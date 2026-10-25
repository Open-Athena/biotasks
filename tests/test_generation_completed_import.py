"""A sealed synthetic lifecycle may be read; active or altered state cannot."""

import pytest
from test_generation_lifecycle import finish
from test_generation_lifecycle import pipeline as pipeline

from biotasks.generation import completed_import, run_generation
from biotasks.validation.files import (
    ValidationError,
    inventory,
    json_sha,
    read_json,
    sha,
    write_json,
)
from biotasks.validation.planning import code_identity


@pytest.fixture
def sealed(pipeline, monkeypatch):
    p, remote = pipeline
    backend = p.root / "backend.yaml"
    backend.write_text("synthetic config, never imported\n")
    p.plan.update(
        generation_code_identity="a" * 64,
        validation_code_identity=code_identity(),
        backend_config_sha256=sha(backend),
    )
    p.plan["backend"]["config"] = str(backend)
    p.plan["plan_identity"] = json_sha({k: v for k, v in p.plan.items() if k != "plan_identity"})
    write_json(p.root / "plan.json", p.plan)
    monkeypatch.setattr(
        completed_import,
        "profiles",
        lambda: [
            {
                "generation_code_identity": "a" * 64,
                "validation_code_identity": code_identity(),
                "assets_sha256": {"family.json": p.group["payload_sha256"]["family.json"]},
            }
        ],
    )
    assert finish(p) == "complete"
    monkeypatch.setattr(p, "client", lambda *a, **k: pytest.fail("No completed-import transport"))
    return p, remote


def test_import_verifies_full_evidence_without_transport_or_mutation(sealed, monkeypatch):
    p, remote = sealed
    before = inventory(p.root)
    count = len(remote["submitted"])
    monkeypatch.setattr(
        completed_import.GenerationPipeline,
        "client",
        lambda *a, **k: pytest.fail("No import transport"),
    )
    assert run_generation.verify(p.root, allow_legacy=True) == p.plan
    assert inventory(p.root) == before and len(remote["submitted"]) == count
    with pytest.raises(ValidationError, match="implementation changed"):
        run_generation.run(p.root, once=True)


@pytest.mark.parametrize(
    "kind", ["intent", "partial", "held", "evidence", "lineage", "model", "cpu", "unknown", "asset"]
)
def test_import_rejects_unsealed_unknown_or_tampered_state(sealed, kind):
    p, _ = sealed
    directory = p.directory
    if kind in {"intent", "partial"}:
        journal = read_json(directory / "journal.json")
        if kind == "intent":
            journal["intent"] = {"stage": "cleanup_verified"}
        else:
            journal["stages"].pop()
        write_json(directory / "journal.json", journal)
    elif kind == "held":
        write_json(directory / "held.json", {"reason": "scientific disagreement"})
    elif kind == "evidence":
        (directory / "cleanup-proof.json").write_text("{}\n")
    elif kind == "lineage":
        target = directory / "generation-source/outputs/raw/README"
        assert target.is_file()
        target.write_text("changed raw generation")
    elif kind in {"model", "cpu"}:
        value = read_json(p.ledger)
        entry = next(
            x
            for x in value["events"]
            if x["kind"]
            == ("model_run_reservation" if kind == "model" else "reserved_cpu_admission")
        )
        entry["state"] = "unresolved"
        write_json(p.ledger, value)
    elif kind == "unknown":
        p.plan["generation_code_identity"] = "b" * 64
    elif kind == "asset":
        p.plan["group"]["payload_sha256"]["family.json"] = "0" * 64
    with pytest.raises(ValidationError):
        completed_import.verify(p.root, p.plan)
