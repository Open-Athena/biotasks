"""Reconstruct native request serialization offline and join retained wire hashes.

All HTTP requests terminate in an in-process synthetic transport. No saved
response is replayed to generation, and no task or model service is contacted.
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import litellm
import openai

from repo2rlenv.llm import complete
from repo2rlenv.pipelines.recipes.terminal.draft import TerminalDraft
from repo2rlenv.spec.input import LLMSpec


def audit(requests, usage):
    rows = []
    upstream = [row for row in map(json.loads, usage.read_text().splitlines())
                if row.get("method") == "POST" and row.get("response_file")]
    original = litellm.completion
    for path in requests:
        native = json.loads(path.read_text())
        # save_record(sort_keys=True) changes nested schema insertion order.
        # Restore the pinned caller's actual schema, after semantic equality.
        schema = TerminalDraft.model_json_schema()
        assert schema == native["response_schema"]
        native["response_schema"] = schema
        seen = []

        def mock(request):
            assert request.url.host == "synthetic.invalid"
            seen.append(request.content)
            return httpx.Response(200, json={"id": "synthetic", "object": "chat.completion",
                "created": 0, "model": "glm-5.3", "choices": [{"index": 0,
                "finish_reason": "stop", "message": {"role": "assistant", "content": "synthetic"}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})

        with httpx.Client(transport=httpx.MockTransport(mock)) as http:
            client = openai.OpenAI(api_key="synthetic-key", base_url="https://synthetic.invalid/v1", http_client=http, max_retries=0)

            def adapted(*args, **kwargs):
                kwargs["client"] = client
                kwargs["extra_body"] = {"chat_template_kwargs": {"reasoning_effort": "medium"}}
                return original(*args, **kwargs)

            with patch.object(litellm, "completion", new=adapted):
                spec = LLMSpec.model_validate({"provider": "openai", "model": "glm-5.3",
                    "endpoint": "https://synthetic.invalid/v1", "timeout_sec": 1200, "fallback": None})
                complete(spec, **native)
        assert len(seen) == 1
        body = json.loads(seen[0])
        assert body["messages"] == [{"role": "system", "content": native["system"]},
                                     {"role": "user", "content": native["user"]}]
        assert body["response_format"]["json_schema"]["schema"] == native["response_schema"]
        assert body["max_tokens"] == native["max_tokens"] == 131072
        assert body["chat_template_kwargs"]["reasoning_effort"] == "medium"
        wire_sha = hashlib.sha256(seen[0]).hexdigest()
        matches = [row for row in upstream if row["request_sha256"] == wire_sha]
        assert len(matches) <= 1
        rows.append({"native_request_file": path.name, "native_request_parent": path.parent.name,
                     "native_request_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "reconstructed_wire_sha256": wire_sha, "wire_body_bytes": len(seen[0]),
                     "wire_field_names": sorted(body), "native_messages_and_schema_preserved": True,
                     "schema_order_restored_from_pinned_native_type": True,
                     "exact_original_wire_match": len(matches) == 1,
                     "original_response": matches[0].get("response_file") if matches else None,
                     "original_response_sha256": matches[0].get("response_sha256") if matches else None,
                     "original_elapsed_seconds": matches[0].get("elapsed_seconds") if matches else None,
                     "original_usage": matches[0].get("usage") if matches else None})
    return {"stage": "offline_native_request_serialization_to_original_wire_hash_attribution",
            "versions": {name: importlib.metadata.version(name) for name in ("litellm", "openai", "httpx")},
            "rows": rows, "model_calls": 0, "live_HTTP_requests": 0,
            "task_fixes": 0, "response_replays_into_generation": 0,
            "limits": ["Only an exact wire hash match establishes request/response association.",
                       "This does not establish why the original caller timed out or what native repairs would do."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-request", type=Path, action="append", required=True)
    parser.add_argument("--usage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.native_request, args.usage)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"requests": len(result["rows"]), "exact_matches": sum(row["exact_original_wire_match"] for row in result["rows"]), "model_calls": 0}))
