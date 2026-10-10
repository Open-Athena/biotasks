"""Regression for the actual LiteLLM nested usage object seen in campaign 001."""

import json
from types import SimpleNamespace

import litellm
from litellm.types.utils import Usage
from repo2rlenv.llm import complete
from repo2rlenv.spec.input import LLMSpec


def test_nested_reasoning_usage_is_preserved_as_json(monkeypatch):
    usage = Usage(
        prompt_tokens=12,
        completion_tokens=9,
        total_tokens=21,
        completion_tokens_details={"reasoning_tokens": 6},
    )
    assert not isinstance(dict(usage)["completion_tokens_details"], dict)
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))], usage=usage
    )
    monkeypatch.setenv("TEST_MODEL_KEY", "fake")
    monkeypatch.setattr(litellm, "completion", lambda **kwargs: response)
    monkeypatch.setattr(litellm, "completion_cost", lambda **kwargs: 0)
    answer = complete(
        LLMSpec(provider="openai", model="fixture", api_key_env="TEST_MODEL_KEY"), user="fixture"
    )
    restored = json.loads(json.dumps(answer.usage))
    assert restored["completion_tokens_details"]["reasoning_tokens"] == 6
    assert restored["prompt_tokens"] == answer.prompt_tokens == 12
    assert restored["completion_tokens"] == answer.completion_tokens == 9
