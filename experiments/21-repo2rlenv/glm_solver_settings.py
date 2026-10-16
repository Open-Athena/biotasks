"""Approved blind-solver settings, separate from generation adaptations."""

from urllib.parse import urlsplit

MODEL = "openai/glm-5.3"
ATTEMPT_TIMEOUT_SEC = 900
MAX_TURNS = 12
MAX_OUTPUT_TOKENS = 2048


def agent_kwargs(api_base):
    route = urlsplit(api_base)
    if (
        route.scheme not in {"http", "https"}
        or not route.hostname
        or route.username
        or route.password
    ):
        raise ValueError("Use the approved service route with credentials supplied separately")
    return {
        "api_base": api_base,
        "max_turns": MAX_TURNS,
        "record_terminal_session": False,
        "llm_call_kwargs": {"max_tokens": MAX_OUTPUT_TOKENS},
    }
