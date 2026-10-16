"""Exercise exact Harbor 0.22.0 query forwarding with a mocked model transport."""

import asyncio
import tempfile
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import litellm
from glm_solver_settings import ATTEMPT_TIMEOUT_SEC, MAX_TURNS, MODEL, agent_kwargs
from harbor.agents.terminus_2.terminus_2 import Terminus2
from harbor.llms.chat import Chat


async def check():
    assert version("harbor") == "0.22.0"
    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        assert kwargs["api_base"] == "https://example.invalid/v1"
        assert kwargs["model"] == MODEL
        assert kwargs["max_tokens"] == 2048
        assert kwargs.get("reasoning_effort") is None
        assert "chat_template_kwargs" not in kwargs.get("extra_body", {})
        return litellm.ModelResponse(
            model=MODEL,
            choices=[
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Synthetic response"},
                }
            ],
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    with tempfile.TemporaryDirectory() as tmp, patch.object(litellm, "acompletion", new=completion):
        agent = Terminus2(
            logs_dir=Path(tmp),
            model_name=MODEL,
            **agent_kwargs("https://example.invalid/v1"),
        )
        assert agent._max_episodes == MAX_TURNS == 12
        assert ATTEMPT_TIMEOUT_SEC == 900
        chat = Chat(agent._llm)
        response = await agent._query_llm(chat, "Synthetic compatibility message")
        assert response.content == "Synthetic response"
        assert len(calls) == 1
    print(
        "PASS: native Harbor query forwards endpoint and 2048-token cap; 12-turn config; zero model calls"
    )


if __name__ == "__main__":
    asyncio.run(check())
