"""Pinned Harbor client can use the uncapped gateway without an invented token limit."""

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from harbor.llms.lite_llm import LiteLLM

from biotasks.inference_gate import Allowance, InferenceGate, RequestLedger


def test_harbor_client_without_output_cap(tmp_path):
    observed = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            observed.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = json.dumps(
                {
                    "id": "fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "glm-5.3",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    gate = InferenceGate(
        upstream=f"http://127.0.0.1:{server.server_port}/v1",
        credential="fixture-secret",
        model="glm-5.3",
        ledger=RequestLedger(tmp_path / "requests.sqlite", {"solver": Allowance(None, None)}),
        deadline=time.time() + 30,
        chat_template_kwargs={"reasoning_effort": "high"},
    ).start()
    try:
        client = LiteLLM(
            "openai/glm-5.3",
            api_base=gate.endpoint("solver"),
            api_key="fixture-secret",
            model_info={
                "max_input_tokens": 262144,
                "input_cost_per_token": 0,
                "output_cost_per_token": 0,
            },
        )
        assert client.get_model_context_limit() == 262144
        response = asyncio.run(client.call("Synthetic compatibility check"))
        assert response.content == "ok"
        assert len(observed) == 1
        assert observed[0]["model"] == "glm-5.3"
        assert observed[0].get("max_tokens") is None
        assert observed[0].get("max_completion_tokens") is None
        assert observed[0]["chat_template_kwargs"] == {"reasoning_effort": "high"}
    finally:
        gate.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
