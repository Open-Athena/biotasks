import json

import pytest
from run_schema_probe import inspect_response, probe_fixture, probe_payload


@pytest.mark.parametrize("mode", ["strict_tool", "json_schema"])
def test_probe_sends_complete_schema_and_detects_missing_and_extra_fields(mode):
    request = probe_payload(mode)
    assert "max_tokens" not in request
    schema = (
        request["tools"][0]["function"]["parameters"]
        if mode == "strict_tool"
        else request["response_format"]["json_schema"]["schema"]
    )
    assert "export_code" in schema["required"]
    for broken in (False, True):
        artifact = probe_fixture()
        if broken:
            del artifact["export_code"]
            artifact["artifacts"][0]["unexpected_field"] = True
        content = json.dumps(artifact)
        message = (
            {"content": content}
            if mode == "json_schema"
            else {"tool_calls": [{"function": {"name": "submit_artifact", "arguments": content}}]}
        )
        result = inspect_response(
            mode, {"choices": [{"finish_reason": "stop", "message": message}]}
        )
        assert result["schema_valid"] is not broken
        if broken:
            assert len(result["errors"]) == 2


def test_delivery_probe_changes_only_server_response_constraint():
    from run_schema_probe import delivery_payload

    plain = delivery_payload("plain_json")
    constrained = delivery_payload("json_schema")
    assert constrained.pop("response_format")["json_schema"]["strict"] is True
    assert constrained == plain
    assert "max_tokens" not in plain
    assert "tools" not in plain


@pytest.mark.parametrize("mode", ["plain_json", "json_schema"])
def test_delivery_probe_detects_semantic_and_newline_corruption(mode):
    from run_schema_probe import delivery_fixture

    for corruption in ("none", "newlines", "placeholder"):
        value = delivery_fixture()
        if corruption == "newlines":
            value["review"] = value["review"].replace("\n", "n")
        if corruption == "placeholder":
            value["validation_plan"] = "placeholder"
        result = inspect_response(
            mode,
            {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value)}}]},
            delivery=True,
        )
        assert result["schema_valid"]
        assert result["exact_fixture_match"] is (corruption == "none")
