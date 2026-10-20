"""Offline preservation, error and deadline checks for generation transport."""
import asyncio
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai

import run_glm_authoring_client_padded as transport


class BrokenCaller(io.BytesIO):
    def write(self, value):
        raise BrokenPipeError("Synthetic disconnected caller")


class PaddedTransportTests(unittest.TestCase):
    def server_fixture(self, status):
        signals = {}
        seen = {"upstream_calls": 0, "statuses": [], "bodies": []}
        body = json.dumps({"model":"glm-5.3", "max_tokens":131072,
            "chat_template_kwargs":{"reasoning_effort":"medium"},
            "messages":[{"role":"user", "content":"Synthetic fixture only."}]}).encode()
        token = "synthetic-application-token-1234567890"
        @contextmanager
        def registered(*args, **kwargs):
            yield "synthetic"
        ctx = SimpleNamespace(get_port=lambda _:0, registry=SimpleNamespace(registered=registered),
            client=SimpleNamespace(resolver_for_job=lambda _:SimpleNamespace(resolve=lambda _:SimpleNamespace(
                endpoints=[SimpleNamespace(url="https://synthetic.invalid/v1")]))))
        modules = {"iris.client.client":SimpleNamespace(iris_ctx=lambda:ctx),
            "iris.cluster.client.job_info":SimpleNamespace(get_job_info=lambda:SimpleNamespace(advertise_host="127.0.0.1")),
            "iris.cluster.types":SimpleNamespace(EndpointAccess=SimpleNamespace(ENDPOINT_ACCESS_LINK=1),
                JobName=SimpleNamespace(from_string=lambda value:value))}
        async def upstream(method, url, raw, key):
            seen["upstream_calls"] += 1
            self.assertEqual(raw, body)
            return status, (b'{"choices":[{"finish_reason":"stop","message":{"content":"unchanged"}}],"usage":{}}'
                            if status == 200 else b'{"error":"synthetic upstream failure"}')
        class FakeServer:
            def __init__(self, address, handler):
                self.server_address = ("127.0.0.1", 12345)
                self.handler = handler
                self.paths = iter(["/v1/chat/completions", "/v1/chat/completions", "/v1/finish"])
            def handle_request(self):
                request = object.__new__(self.handler)
                request.command = "POST"
                request.path = next(self.paths)
                request.headers = {"Content-Length":str(len(body)), "X-Biotasks21-Inference-Token":token}
                request.rfile = io.BytesIO(body)
                request.wfile = io.BytesIO()
                request.send_response = lambda status:seen["statuses"].append(status)
                request.send_header = lambda *args:None
                request.end_headers = lambda:None
                request.dispatch()
                seen["bodies"].append(json.loads(request.wfile.getvalue()))
            def server_close(self):
                pass
        with tempfile.TemporaryDirectory() as directory:
            env = {"IRIS_OUTPUT_DIR":directory, "BIOTASKS21_INFERENCE_CLIENT_TOKEN":token,
                "BIOTASKS21_GLM_KEY":"synthetic", "BIOTASKS21_GLM_RELAY_JOB":"/synthetic/relay",
                "DAYTONA_API_KEY":"", "REPO2RLENV_REMOTE_WORKER":"", "BIOTASKS21_TRANSPORT_ONLY":"0"}
            with patch.dict(os.environ, env), patch.dict(sys.modules, modules), \
                 patch.object(transport, "Server", FakeServer), \
                 patch.object(transport, "upstream_response", upstream), \
                 patch.object(transport.signal, "signal", side_effect=lambda sig, fn:signals.update({sig:fn})):
                transport.main()
            seen["rows"] = [json.loads(line) for line in (Path(directory)/"inference-usage.jsonl").read_text().splitlines()]
            seen["responses"] = [file.read_bytes() for file in (Path(directory)/"responses").glob("*")]
            seen["requests"] = [{"name":file.name, "raw":file.read_bytes(), "mode":file.stat().st_mode & 0o777}
                                for file in (Path(directory)/"requests").glob("*")]
        return seen

    def test_duplicate_native_request_is_not_forwarded_again(self):
        seen = self.server_fixture(200)
        self.assertEqual(seen["upstream_calls"], 1)
        self.assertEqual(seen["statuses"][:2], [200, 409])
        self.assertEqual(seen["bodies"][0]["choices"][0]["message"]["content"], "unchanged")
        self.assertEqual(sum(row.get("model_calls", 0) for row in seen["rows"]), 1)

    def test_upstream_status_and_raw_error_are_archived_without_a_completion(self):
        seen = self.server_fixture(503)
        self.assertEqual(seen["upstream_calls"], 1)
        self.assertEqual(seen["bodies"][0], json.loads(transport.FAILURE))
        self.assertEqual(seen["rows"][0]["upstream_status"], 503)
        self.assertEqual(seen["responses"], [b'{"error":"synthetic upstream failure"}'])

    def test_wire_request_and_dispatch_receipt_remain_associated_with_response(self):
        seen = self.server_fixture(200)
        request = next(file for file in seen["requests"] if not file["name"].endswith("-receipt.json"))
        receipt = next(file for file in seen["requests"] if file["name"].endswith("-receipt.json"))
        metadata = json.loads(receipt["raw"])
        self.assertEqual(request["name"], metadata["request_sha256"] + ".json")
        self.assertEqual(metadata["status"], "response_captured")
        self.assertIn(metadata["request_sha256"], metadata["response_file"])
        self.assertEqual(request["mode"], 0o600)
        self.assertEqual(receipt["mode"], 0o600)

    def handler(self, *, broken=False):
        seen = {}
        handler = SimpleNamespace(wfile=BrokenCaller() if broken else io.BytesIO(),
            send_response=lambda status: seen.update(status=status),
            send_header=lambda name, value: seen.update({name: value}),
            end_headers=lambda: None)
        return handler, seen

    def test_original_successful_JSON_bytes_and_native_SDK_fields_preserved(self):
        original = b'{"id":"fixture","object":"chat.completion","created":0,"model":"glm-5.3","choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":"unchanged \\n answer"}}],"usage":{"prompt_tokens":7,"completion_tokens":9,"total_tokens":16}}'
        handler, seen = self.handler()
        row = {}
        transport.padded_reply(handler, lambda: original, row)
        raw = handler.wfile.getvalue()
        self.assertEqual(len(raw), int(seen["Content-Length"]))
        self.assertEqual(raw.strip(), original)
        self.assertEqual(json.loads(raw), json.loads(original))
        def response(request):
            return httpx.Response(200, content=raw, headers={"Content-Type": "application/json"})
        with httpx.Client(transport=httpx.MockTransport(response)) as http:
            client = openai.OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1", http_client=http, max_retries=0)
            result = client.chat.completions.create(model="glm-5.3", messages=[{"role":"user","content":"fixture"}])
        self.assertEqual(result.choices[0].message.content, "unchanged \n answer")
        self.assertEqual(result.usage.completion_tokens, 9)

    def test_upstream_error_cannot_supply_a_model_choice(self):
        handler, _ = self.handler()
        calls = []
        def failure():
            calls.append(1)
            raise TimeoutError("Synthetic timeout")
        row = {}
        transport.padded_reply(handler, failure, row)
        self.assertEqual(calls, [1])
        raw = handler.wfile.getvalue()
        self.assertEqual(json.loads(raw), json.loads(transport.FAILURE))
        self.assertNotIn("choices", json.loads(raw))
        self.assertEqual(row["error_type"], "TimeoutError")

    def test_disconnected_caller_does_not_interrupt_upstream_capture(self):
        handler, _ = self.handler(broken=True)
        captured = []
        def fetch():
            captured.append(b'{"original":"retained"}')
            return captured[-1]
        row = {}
        transport.padded_reply(handler, fetch, row)
        self.assertEqual(captured, [b'{"original":"retained"}'])
        self.assertTrue(row["caller_disconnected"])

    def test_async_request_has_wall_deadline_and_closes_client(self):
        seen = {}
        class Client:
            def __init__(self, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                seen["closed"] = True
            @asynccontextmanager
            async def stream(self, *args, **kwargs):
                async def blocks():
                    await asyncio.sleep(1)
                    yield b"never before deadline"
                yield SimpleNamespace(status_code=200, aiter_bytes=blocks)
        with patch.object(transport.httpx, "AsyncClient", Client), patch.object(transport, "DEADLINE", 0.01):
            with self.assertRaises(TimeoutError):
                asyncio.run(transport.upstream_response("POST", "https://synthetic.invalid/v1", b"original", "synthetic"))
        self.assertTrue(seen["closed"])

    def test_async_forward_preserves_request_and_bounded_response(self):
        seen = {}
        class Client:
            def __init__(self, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            @asynccontextmanager
            async def stream(self, method, url, **kwargs):
                seen.update(method=method, body=kwargs["content"])
                async def blocks():
                    yield b"abc"
                    yield b"def"
                yield SimpleNamespace(status_code=201, aiter_bytes=blocks)
        with patch.object(transport.httpx, "AsyncClient", Client):
            result = asyncio.run(transport.upstream_response("POST", "https://synthetic.invalid/v1", b"original", "synthetic"))
            self.assertEqual(result, (201, b"abcdef"))
            self.assertEqual(seen, {"method":"POST", "body":b"original"})
            with patch.object(transport, "MAX_RESPONSE_BYTES", 5), self.assertRaises(ValueError):
                asyncio.run(transport.upstream_response("POST", "https://synthetic.invalid/v1", b"original", "synthetic"))


if __name__ == "__main__":
    unittest.main()
