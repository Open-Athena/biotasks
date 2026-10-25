"""Early review grounds findings and never replenishes the quality allowance.

Synthetic workers test the interface and routing, not scientific validity.
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path

import pytest
from specification_inputs import specification_context
from specification_protocol import (
    SpecificationReview,
    specification_review_context,
    validate_specification_review,
)


def proposal():
    return {
        "disposition": "draft_ready",
        "review": "WRITER_SELF_REVIEW_MUST_BE_WITHHELD",
        "task_brief": "Compute the result.",
        "validation_handoff": "Define the measurement before calibrating its precision.",
    }


def finding():
    return {
        "problem": "The requested quantity is unspecified.",
        "evidence": [{"path": "proposal/task_brief", "quote": "Compute the result."}],
        "required_change": "Define the quantity using the source evidence.",
    }


def test_review_withholds_writer_assessment_and_prior_feedback_without_mutation():
    original = {
        "files": {"source.py": "observed = measure(data)\n", "metadata.json": {"rows": 5}},
        "file_sha256": {"source.py": "b" * 64},
        "revision_context": {"old_review": "Do not anchor the next reviewer"},
    }
    before = json.dumps(original)
    context = specification_review_context(original, proposal(), parent_sha256="a" * 64)
    assert json.dumps(original) == before
    assert "files" not in context and "revision_context" not in context
    assert "WRITER_SELF_REVIEW_MUST_BE_WITHHELD" not in json.dumps(context)
    assert context["evidence_text"]["source.py"] == original["files"]["source.py"]
    assert context["evidence_text"]["metadata.json"] == '{\n  "rows": 5\n}'
    assert context["specification_review"]["parent_sha256"] == "a" * 64


@pytest.mark.parametrize(
    "disposition,findings", [("ready", [finding()]), ("revise", []), ("reject", [])]
)
def test_review_cannot_hide_blockers_or_make_an_ungrounded_refusal(disposition, findings):
    with pytest.raises(ValueError, match="Ready requires"):
        SpecificationReview(disposition=disposition, assessment="Assessment", findings=findings)


@pytest.mark.parametrize("defect", ["changed_quote", "unknown_path", "whitespace"])
def test_finding_requires_an_exact_available_quote(defect):
    context = specification_review_context({"files": {}}, proposal(), parent_sha256="a" * 64)
    item = finding()
    item["evidence"][0].update(
        {"quote": "Invented fact"}
        if defect == "changed_quote"
        else {"path": "unseen/source.py"}
        if defect == "unknown_path"
        else {"quote": " "}
    )
    with pytest.raises(ValueError):
        validate_specification_review(
            {"disposition": "revise", "assessment": "Assessment", "findings": [item]}, context
        )


@pytest.mark.parametrize("valid_quote", [False, True])
def test_actual_review_worker_uses_separate_prompt_and_validates_grounding(tmp_path, valid_quote):
    from run_specification import run

    experiment = Path(__file__).parent
    config = json.loads((experiment / "specification-diagnostic-config.json").read_text())
    raw = (json.dumps(proposal()) + "\n").encode()
    parent = tmp_path / "proposal.json"
    parent.write_bytes(raw)
    context = specification_context(
        experiment / config["reference_directory"],
        json.loads((experiment / config["policy_file"]).read_text()),
    )
    context = specification_review_context(
        context, proposal(), parent_sha256=hashlib.sha256(raw).hexdigest()
    )
    input_file = tmp_path / "review-input.json"
    input_file.write_text(json.dumps(context))
    config.update(
        specification_review=True,
        specification_proposal_file=str(parent),
        input_file=str(input_file),
        output_format="json_schema",
        max_requests=1,
    )
    calls = []
    value = {
        "disposition": "revise",
        "assessment": "Definition is missing",
        "findings": [finding()],
    }
    if not valid_quote:
        value["findings"][0]["evidence"][0]["quote"] = "Never present in the evidence"

    async def complete(payload):
        calls.append(payload)
        assert "Independently review" in payload["messages"][0]["content"]
        assert "WRITER_SELF_REVIEW_MUST_BE_WITHHELD" not in json.dumps(payload)
        assert "max_tokens" not in payload
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps(value)},
                }
            ]
        }

    root = tmp_path / "review"
    task = run(
        config,
        root=root,
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if valid_quote:
        asyncio.run(task)
        assert json.loads((root / "specification-review.json").read_text()) == value
    else:
        with pytest.raises(RuntimeError):
            asyncio.run(task)
        assert not (root / "specification-review.json").exists()
    assert len(calls) == 1 and parent.read_bytes() == raw
    result = json.loads((root / "result.json").read_text())
    assert result["specification_review_enabled"]
    assert result["daytona_sandboxes_created"] == 0
    assert not result["scientific_analysis_executed"] and not result["construction_run"]


@pytest.mark.parametrize(
    "initial,final,revision_ready,expected",
    [
        ("ready", None, True, "original"),
        ("reject", None, True, "rejected"),
        ("revise", "ready", True, "revised"),
        ("revise", "revise", True, "rejected"),
        ("revise", "reject", True, "rejected"),
        ("revise", None, False, "rejected"),
        ("ready", None, True, "changed_during_review"),
    ],
)
def test_review_route_preserves_originals_and_performs_at_most_one_repair(
    tmp_path, monkeypatch, initial, final, revision_ready, expected
):
    import sys
    import types

    from run_autonomous import Pipeline, Rejected

    module = sys.modules[Pipeline.__module__]
    monkeypatch.setattr(module, "HERE", tmp_path)
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "private://fixture")
    context = {"files": {"source.py": "observed = measure(data)\n"}}
    monkeypatch.setitem(
        sys.modules,
        "specification_inputs",
        types.SimpleNamespace(specification_context=lambda *a, **k: context),
    )
    root = tmp_path / "run"
    original = root / "specification"
    module.write(original / "specification.json", proposal())
    raw = (original / "specification.json").read_bytes()
    replay = root / "replay"
    module.write(replay / "result.json", {})
    config = {
        "campaign": "fixture",
        "factory_revision": "fixture",
        "notebook_file": "source.ipynb",
        "daytona_budget_usd": "5",
    }
    pipeline = Pipeline(
        config,
        root=root,
        seed={},
        deadline=time.time() + 7200,
        endpoint="unused",
        credential="unused",
    )
    calls = []

    async def worker(config, *, root, deadline, **kwargs):
        calls.append(root.name)
        assert deadline == pipeline.deadline - 300
        if config.get("specification_review"):
            decision = initial if root.name == "specification-review" else final
            value = {
                "disposition": decision,
                "assessment": "Fixture review",
                "findings": [] if decision == "ready" else [finding()],
            }
            observed = module.read(tmp_path / config["input_file"])
            validate_specification_review(value, observed)
            module.write(root / "specification-review.json", value)
            if expected == "changed_during_review":
                (original / "specification.json").write_bytes(raw + b" ")
        else:
            feedback = module.read(tmp_path / config["revision_context_file"])
            assert feedback["independent_review"]["disposition"] == "revise"
            changed = proposal()
            if not revision_ready:
                changed.update(disposition="reject", task_brief="")
            module.write(root / "specification.json", changed)

    job = pipeline.review_specification(
        spec=original,
        reference=root / "reference",
        policy={},
        replay=replay,
        base={"policy_file": "policy.json"},
        specify=worker,
    )
    if expected == "changed_during_review":
        with pytest.raises(ValueError, match="changed during"):
            asyncio.run(job)
        assert "effective_specification" not in pipeline.receipt
    elif expected == "rejected":
        with pytest.raises(Rejected):
            asyncio.run(job)
    else:
        effective = asyncio.run(job)
        assert effective == (
            original if expected == "original" else root / "specification-revision"
        )
    assert (original / "specification.json").read_bytes() == (
        raw + b" " if expected == "changed_during_review" else raw
    )
    assert calls.count("specification-revision") == (initial == "revise")
    assert calls.count("specification-review-revised") == (initial == "revise" and revision_ready)
    assert pipeline.receipt["daytona_reserved_usd"] == 0
    if initial == "revise":
        assert pipeline.receipt["quality_repair"]["allowance_consumed"]
        assert pipeline.receipt["quality_repair"]["kind"] == "specification_review"
    else:
        assert "quality_repair" not in pipeline.receipt
