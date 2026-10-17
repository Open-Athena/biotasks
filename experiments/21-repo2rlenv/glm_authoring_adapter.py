"""Explicit generation-only GLM adaptation; preserve upstream authoring logic."""

from contextlib import contextmanager
from unittest.mock import patch

import litellm
from repo2rlenv.campaigns import structured
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_smith import issue
from repo2rlenv.pipelines.recipes.seta_seed2synth import recipe as seta


@contextmanager
def adapted_authoring(settings, output, *, metering_target="swe_smith"):
    """Override the recorded output allowance and retain raw response evidence.

    This context is serial and process-local. Native candidate and repair bounds
    remain in write_issue; the original recipe implementation is not edited.
    """
    targets = {"swe_smith": issue, "structured": structured, "seta_seed2synth": seta}
    target = targets[metering_target]
    original_metered = target.metered_complete
    original_completion = litellm.completion
    calls = 0

    def completion(*args, **kwargs):
        nonlocal calls
        calls += 1
        extra = dict(kwargs.get("extra_body") or {})
        template = dict(extra.get("chat_template_kwargs") or {})
        template["reasoning_effort"] = settings["reasoning_effort"]
        extra["chat_template_kwargs"] = template
        kwargs["extra_body"] = extra
        # Native metering already preserves the prompt and dispatched receipt.
        raw = original_completion(*args, **kwargs)
        choice = raw.choices[0]
        save_record(
            output / "raw" / f"call-{calls:03d}.json",
            {
                "finish_reason": choice.finish_reason,
                "content": choice.message.content,
                "reasoning_content": getattr(choice.message, "reasoning_content", None),
                "usage": raw.usage.model_dump(mode="json") if raw.usage else None,
                "requested_max_tokens": kwargs["max_tokens"],
                "requested_reasoning_effort": settings["reasoning_effort"],
                "requested_timeout_sec": settings["request_timeout_sec"],
            },
        )
        return raw

    def metered(*args, **kwargs):
        kwargs["max_tokens"] = settings["max_output_tokens"]
        return original_metered(*args, **kwargs)

    with (
        patch.object(target, "metered_complete", new=metered),
        patch.object(litellm, "completion", new=completion),
    ):
        yield
