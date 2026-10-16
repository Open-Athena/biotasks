"""Offline check of actual metering, repair bounds, and adapted wire settings."""

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import litellm
from glm_authoring_adapter import adapted_authoring
from litellm.types.utils import Usage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.pipelines.recipes.swe_smith import issue
from repo2rlenv.spec.input import LLMSpec

root = Path(__file__).resolve().parent
settings = json.loads((root / "glm-generation-adaptation.json").read_text())
os.environ["BIOTASKS21_OFFLINE_KEY"] = "offline-fixture"
spec = LLMSpec(
    provider="openai",
    model="glm-5.3",
    endpoint="https://example.invalid/v1",
    api_key_env="BIOTASKS21_OFFLINE_KEY",
    timeout_sec=settings["request_timeout_sec"],
    fallback=None,
)
calls = []


def transport(*args, **kwargs):
    calls.append(kwargs)
    assert kwargs["max_tokens"] == 131072
    assert kwargs["timeout"] == 1200
    assert kwargs["num_retries"] == 0
    assert kwargs["extra_body"]["chat_template_kwargs"]["reasoning_effort"] == "medium"
    # Invalid JSON on both attempts must exhaust the upstream repair bound.
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="length",
                message=SimpleNamespace(content="", reasoning_content="fixture reasoning"),
            )
        ],
        usage=Usage(
            prompt_tokens=7,
            completion_tokens=15,
            total_tokens=22,
            completion_tokens_details={"reasoning_tokens": 15},
        ),
    )


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)
    ledger = BudgetLedger(out / "ledger.sqlite", limit_usd="5")
    with (
        patch.object(litellm, "completion", new=transport),
        patch.object(issue, "issue_context", return_value="Synthetic test context"),
        adapted_authoring(settings, out),
    ):
        try:
            issue.write_issue(
                out,
                {"id": "synthetic"},
                spec,
                ledger,
                out / "receipt.json",
                operation_id="offline",
            )
        except ValueError as exc:
            assert "bounded attempts" in str(exc)
        else:
            raise AssertionError("Empty answers must fail authoring")
    assert len(calls) == 2
    for stem in ("receipt", "receipt-attempt-2"):
        request = json.loads((out / f"{stem}.request.json").read_text())
        receipt = json.loads((out / f"{stem}.json").read_text())
        assert request["max_tokens"] == 131072
        assert receipt["status"] == "completed"
        assert receipt["response"]["usage"]["completion_tokens_details"]["reasoning_tokens"] == 15
    for index in (1, 2):
        raw = json.loads((out / "raw" / f"call-{index:03d}.json").read_text())
        assert raw["finish_reason"] == "length"
        assert raw["reasoning_content"] == "fixture reasoning"
print(
    "PASS: adapted wire settings, durable raw/normalized evidence, native repair bound; zero model calls"
)
