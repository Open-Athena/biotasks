"""The campaign uses native effort values, without silently mapping aliases."""

import pytest
from model_profile import native_effort

from biotasks.chat_author import ChatLimits


def test_default_is_native_middle_level():
    assert native_effort({}) == "high"


@pytest.mark.parametrize("effort", ["low", "high", "max"])
def test_explicit_native_values_reach_author_limits(effort):
    assert (
        ChatLimits(reasoning_effort=native_effort({"reasoning_effort": effort})).reasoning_effort
        == effort
    )


@pytest.mark.parametrize("effort", ["medium", None, "HIGH", "", [], 1])
def test_non_native_values_are_rejected(effort):
    with pytest.raises(ValueError, match="native reasoning_effort"):
        native_effort({"reasoning_effort": effort})
