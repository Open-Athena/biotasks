"""The notebook adaptation preserves upstream design calls and schema."""

import json
from types import SimpleNamespace

from repo2rlenv.pipelines.recipes.seta_seed2synth import recipe


def test_guidance_is_optional_and_preserves_upstream_contract(monkeypatch):
    calls = []

    def complete(model, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            content=json.dumps(
                {
                    "core_capabilities": ["analysis"],
                    "draft_spec": "x" * 100,
                }
            )
        )

    monkeypatch.setattr(recipe, "metered_complete", complete)
    kwargs = dict(model=None, ledger=None, receipt=None, operation_id="test", resume=False)
    original = recipe.design({"question_text": "source"}, **kwargs)
    adapted = recipe.design(
        {"question_text": "source"}, system_guidance="Retain real data.", **kwargs
    )
    assert original == adapted
    assert calls[1]["system"] == calls[0]["system"] + "\n\nRetain real data."
    for key in ("user", "response_schema", "max_tokens", "reservation_usd", "resume"):
        assert calls[0][key] == calls[1][key]
