import hashlib
import json

import pytest

from biotasks.factory_batch import freeze_batch
from biotasks.factory_budget import SessionBudget
from biotasks.factory_controller import WorkerEvidence, decide
from biotasks.factory_dispatch import dispatch
from biotasks.factory_handoff import freeze_followup


def test_fixed_stages_use_original_templates_and_allow_distinct_turn_budgets(tmp_path):
    limits = {
        name: {"request_cap": calls, "wall_seconds": seconds, "output_cap": 16384}
        for name, calls, seconds in [
            ("specification", 12, 300),
            ("construction", 60, 1200),
            ("review", 24, 600),
            ("repair", 40, 900),
            ("review_after_repair", 24, 600),
        ]
    }
    source = tmp_path / "inputs.zip"
    source.write_bytes(b"source")
    root = tmp_path / "batch.json"
    root_hash = freeze_batch(
        "a" * 40,
        {"novel": source},
        {},
        12,
        300,
        1,
        root,
        workflow_version=2,
        stage_limits=limits,
    )["sha256"]
    ledger = SessionBudget(tmp_path / "budget.sqlite", 5, 5, 1)
    calls = []

    def remote(session, batch, archive):
        calls.append((session, batch["entries"]["novel"]))
        return f"job-{len(calls)}"

    parent = {}
    path, digest, archive = root, root_hash, source
    for slot in limits:
        if slot != "specification":
            path, archive = tmp_path / f"{slot}.json", tmp_path / f"{slot}.zip"
            descriptor = {
                "artifact_prefix": "s3://example/prior",
                "input_zip_sha256": "b" * 64,
                "generated_manifest": [],
                "deleted_inputs": [],
                "task_manifest": [],
            }
            digest = freeze_followup(
                root,
                root_hash,
                "novel",
                slot,
                parent,
                descriptor,
                {"result.json": b"{}"},
                limits[slot]["request_cap"],
                limits[slot]["wall_seconds"],
                archive,
                path,
            )["sha256"]
            # A fresh hash is not permission to alter a frozen stage budget.
            altered = json.loads(path.read_text())
            altered["stage_templates"][slot]["request_cap"] = 59
            altered["entries"]["novel"]["request_cap"] = 59
            modified = tmp_path / f"{slot}-altered.json"
            modified.write_text(json.dumps(altered))
            with pytest.raises(ValueError, match="templates changed"):
                dispatch(
                    modified,
                    hashlib.sha256(modified.read_bytes()).hexdigest(),
                    "novel",
                    archive,
                    ledger,
                    remote,
                )
        job = dispatch(path, digest, "novel", archive, ledger, remote)
        session = calls[-1][0]
        ledger.terminal(session, job, "succeeded")
        with ledger.connect() as db:
            spec_hash = db.execute(
                "SELECT spec_sha256 FROM sessions WHERE id=?", (session,)
            ).fetchone()[0]
        parent = {"session_id": session, "job_id": job, "spec_sha256": spec_hash}
    assert [spec["request_cap"] for _, spec in calls] == [12, 60, 24, 40, 24]
    assert len({session for session, _ in calls}) == 5


def test_seed_rejection_is_terminal_without_native_validation(tmp_path):
    (tmp_path / "seed.json").write_text(json.dumps({"source_sha256": "a" * 64}))
    proposal = {
        "schema_version": 1,
        "status": "rejected",
        "source_sha256": "a" * 64,
        "rationale": "The supplied input cannot support the proposed scientific question.",
        "evidence_paths": ["seed.json"],
    }
    (tmp_path / "proposal.json").write_text(json.dumps(proposal))
    worker = WorkerEvidence("specification", "succeeded", "worker_finished", True, "b" * 64)
    assert decide(worker, None, workspace=tmp_path).action == "rejected"
    proposal["source_sha256"] = "c" * 64
    (tmp_path / "proposal.json").write_text(json.dumps(proposal))
    assert decide(worker, None, workspace=tmp_path).action == "specification_incomplete"
    worker = WorkerEvidence("construction", "succeeded", "worker_finished", True, "b" * 64)
    (tmp_path / "rejection.md").write_text("Input provenance remains unresolved; see seed.json.")
    assert decide(worker, None, workspace=tmp_path).action == "rejected"


def test_specification_requires_coherent_subgoals_before_construction(tmp_path):
    (tmp_path / "seed.json").write_text(json.dumps({"source_sha256": "a" * 64}))
    proposal = {
        "schema_version": 1,
        "status": "specified",
        "source_sha256": "a" * 64,
        "rationale": "Compact analysis",
        "evidence_paths": ["seed.json"],
        "objective": "Analyze biological sample measurements",
        "methodology": ["Specify filtering"],
        "inputs": [
            {
                "path": "input.tsv",
                "identity": "observed measurements",
                "origin": "source",
                "preparation": "Unmodified",
            }
        ],
        "deliverables": [{"path": "/app/result.tsv", "description": "Result table"}],
        "subgoals": [
            {"id": "a", "weight": 0.5, "description": "Filtering", "depends_on": []},
            {"id": "b", "weight": 0.5, "description": "Analysis", "depends_on": ["a"]},
        ],
        "reference_ecosystem": "Native source ecosystem",
        "validation_strategy": "Recorded controls",
        "runtime_rationale": "Small inputs",
        "unresolved": [],
    }
    worker = WorkerEvidence("specification", "succeeded", "worker_finished", True, "b" * 64)
    path = tmp_path / "proposal.json"
    path.write_text(json.dumps(proposal))
    assert decide(worker, None, workspace=tmp_path).action == "construction"
    proposal["subgoals"][0]["depends_on"] = ["b"]
    path.write_text(json.dumps(proposal))
    assert decide(worker, None, workspace=tmp_path).action == "specification_incomplete"
