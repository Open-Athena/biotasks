import concurrent.futures
import http.client
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from biotasks.inference_gate import Allowance, InferenceGate, RequestLedger


def test_uncertain_requests_count_and_limits_cannot_change(tmp_path):
    ledger = RequestLedger(tmp_path / "calls.db", {"solve": Allowance(3, 100)})

    def claim(_):
        try:
            return ledger.claim("solve", b"private prompt")
        except RuntimeError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(claim, range(6)))
    assert sum(value is not None for value in results) == 3
    with pytest.raises(ValueError, match="Cannot change"):
        RequestLedger(tmp_path / "calls.db", {"solve": Allowance(4, 100)})
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls WHERE state='uncertain'").fetchone()[0] == 3
        assert "private prompt" not in str(list(db.iterdump()))


@pytest.mark.parametrize("settings", [None, {"reasoning_effort": "low"}])
@pytest.mark.parametrize("output_mode", ["json_schema", "json_object"])
def test_gate_forwards_once_then_blocks_retries_and_bad_payloads(tmp_path, settings, output_mode):
    observed = []

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_POST(self):
            observed.append(
                (
                    self.path,
                    self.headers["Authorization"],
                    self.rfile.read(int(self.headers["Content-Length"])),
                )
            )
            # A provider failure still consumes the one permitted request.
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'{"error":"unavailable"}')

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    worker = threading.Thread(target=upstream.serve_forever, daemon=True)
    worker.start()
    ledger = RequestLedger(tmp_path / "calls.db", {"solve": Allowance(1, 128)})
    gate = InferenceGate(
        upstream=f"http://127.0.0.1:{upstream.server_port}/v1",
        credential="TEST_SECRET",
        model="fixture",
        ledger=ledger,
        deadline=time.time() + 10,
        chat_template_kwargs=settings,
        structured_output_mode=output_mode,
    ).start()
    route = urlsplit(gate.endpoint("solve"))

    def request(tokens=64, key="TEST_SECRET", **extra):
        assert route.hostname is not None
        client = http.client.HTTPConnection(route.hostname, route.port, timeout=2)
        try:
            client.request(
                "POST",
                route.path + "/chat/completions",
                body=json.dumps(
                    {
                        "model": "fixture",
                        "max_tokens": tokens,
                        "messages": [{"role": "user", "content": "PRIVATE_PROMPT"}],
                        **extra,
                    }
                ),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            )
            reply = client.getresponse()
            reply.read()
            return reply.status
        finally:
            client.close()

    try:
        schema = {"type": "object", "properties": {"code": {"type": "string"}}}
        output_format = {"type": "json_schema", "json_schema": {"schema": schema}}
        assert request(key="wrong") == 401
        assert request(tokens=129) == 400
        if settings:
            assert request(chat_template_kwargs={"reasoning_effort": "high"}) == 400
        assert request(response_format=output_format) == 503
        assert request() == 429
        assert len(observed) == 1
        assert observed[0][0:2] == ("/v1/chat/completions", "Bearer TEST_SECRET")
        payload = json.loads(observed[0][2])
        assert payload.get("chat_template_kwargs") == settings
        assert payload["max_tokens"] == 64
        assert payload["messages"][0]["content"] == "PRIVATE_PROMPT"
        if output_mode == "json_object":
            assert payload["response_format"] == {"type": "json_object"}
            assert json.dumps(schema) in payload["messages"][-1]["content"]
        else:
            assert payload["response_format"] == output_format
            assert len(payload["messages"]) == 1
        with sqlite3.connect(ledger.path) as db:
            dump = str(list(db.iterdump()))
        assert "TEST_SECRET" not in dump
        assert "PRIVATE_PROMPT" not in dump
    finally:
        gate.close()
        upstream.shutdown()
        upstream.server_close()
        worker.join(timeout=2)


def test_exhausted_scope_stays_disabled_on_continuation(tmp_path):
    ledger = RequestLedger(tmp_path / "disabled.db", {"compatibility": Allowance(0, 512)})
    with pytest.raises(RuntimeError, match="allowance exhausted"):
        ledger.claim("compatibility", b"unused")
