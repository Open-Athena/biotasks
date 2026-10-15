import json

import pytest
from run_schema_probe import inspect_response, probe_fixture, probe_payload


@pytest.mark.parametrize("mode", ["strict_tool", "json_schema"])
def test_probe_sends_complete_schema_and_detects_missing_and_extra_fields(mode):
    request = probe_payload(mode)
    assert "max_tokens" not in request
    schema = request["tools"][0]["function"]["parameters"] if mode == "strict_tool" else request["response_format"]["json_schema"]["schema"]
    assert "export_code" in schema["required"]
    for broken in (False, True):
        artifact = probe_fixture()
        if broken:
            del artifact["export_code"]
            artifact["artifacts"][0]["unexpected_field"] = True
        content = json.dumps(artifact)
        message = {"content": content} if mode == "json_schema" else {"tool_calls": [{"function": {"name": "submit_artifact", "arguments": content}}]}
        result = inspect_response(mode, {"choices": [{"finish_reason": "stop", "message": message}]})
        assert result["schema_valid"] is not broken
        if broken:
            assert len(result["errors"]) == 2
