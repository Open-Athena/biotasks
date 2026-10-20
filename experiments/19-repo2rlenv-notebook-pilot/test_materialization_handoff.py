"""Scientific caveats must survive the handoff; downstream work plans stay separate."""

import json

from task_materialization import materialization_context


def test_preserve_scientific_review_and_repeatability(tmp_path):
    (tmp_path / "trial").mkdir()
    (tmp_path / "trial/inputs-before.json").write_text(json.dumps({"inputs": []}))
    context = {
        "specification": {
            "task_brief": "Proposed question",
            "review": "Observed uncertainty",
            "validation_handoff": "Later mutation suite",
        },
        "repeatability": {"comparison_rules_validated": False},
        "policy": {},
        "source_evidence": {},
        "reference_observations": {},
        "paths": {},
    }
    result = materialization_context(context, tmp_path, 600)
    assert result["specification"]["review"] == "Observed uncertainty"
    assert result["repeatability"] == context["repeatability"]
    assert "validation_handoff" not in result["specification"]
    assert context["specification"]["validation_handoff"] == "Later mutation suite"
