"""Count outgoing chat-completion requests, including retries, on a local host.

This is a loopback-only adapter for a pre-authorized inference service. It does
not launch models. Credentials, prompts and responses are never written to its
ledger; normal pipeline clients remain responsible for their execution evidence.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Allowance:
    requests: int
    output_tokens: int


class RequestLedger:
    def __init__(self, path: Path, allowances: dict[str, Allowance]):
        self.path, self.allowances = path, allowances
        if not allowances or any(
            v.requests < 0 or v.output_tokens < 1 for v in allowances.values()
        ):
            raise ValueError("Nonnegative request and positive output-token bounds are required")
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            config = json.dumps(
                {k: [v.requests, v.output_tokens] for k, v in allowances.items()}, sort_keys=True
            )
            db.execute("INSERT OR IGNORE INTO settings VALUES ('allowances', ?)", (config,))
            if (
                db.execute("SELECT value FROM settings WHERE key='allowances'").fetchone()[0]
                != config
            ):
                raise ValueError("Cannot change allowances for an existing campaign")
            db.execute(
                "CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, scope TEXT, digest TEXT, state TEXT)"
            )

    def claim(self, scope: str, body: bytes) -> int:
        limit = self.allowances[scope]
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM calls WHERE scope=?", (scope,)).fetchone()[0]
            if count >= limit.requests:
                raise RuntimeError("Request allowance exhausted")
            result = db.execute(
                "INSERT INTO calls(scope,digest,state) VALUES (?,?,?)",
                (scope, hashlib.sha256(body).hexdigest(), "uncertain"),
            )
            assert result.lastrowid is not None
            return result.lastrowid

    def finish(self, call_id: int, state: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE calls SET state=? WHERE id=?", (state, call_id))


class InferenceGate:
    def __init__(
        self,
        *,
        upstream: str,
        credential: str,
        model: str,
        ledger: RequestLedger,
        deadline: float,
        request_timeout: float = 180,
        chat_template_kwargs: dict[str, str] | None = None,
        structured_output_mode: str = "json_schema",
    ):
        route = urlsplit(upstream)
        if (
            route.scheme not in {"http", "https"}
            or not route.hostname
            or route.username
            or route.password
            or route.query
            or route.fragment
        ):
            raise ValueError("An HTTP(S) base URL without embedded credentials is required")
        if not credential or deadline <= time.time() or request_timeout <= 0:
            raise ValueError("Credential, future deadline and finite timeout are required")
        if structured_output_mode not in {"json_schema", "json_object"}:
            raise ValueError("Unsupported structured-output mode")
        self.route, self.credential, self.model = route, credential, model
        self.ledger, self.deadline, self.request_timeout = ledger, deadline, request_timeout
        self.chat_template_kwargs = dict(chat_template_kwargs or {})
        self.structured_output_mode = structured_output_mode
        gate = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def reject(self, status, message):
                body = json.dumps({"error": {"message": message}}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                parts = self.path.split("/")
                if (
                    len(parts) != 5
                    or parts[2:] != ["v1", "chat", "completions"]
                    or parts[1] not in gate.ledger.allowances
                ):
                    return self.reject(404, "Unsupported inference route")
                if not hmac.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + gate.credential
                ):
                    return self.reject(401, "Authentication required")
                remaining = gate.deadline - time.time()
                if remaining <= 0:
                    return self.reject(429, "Campaign deadline reached")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16 * 1024 * 1024:
                        raise ValueError
                    self.connection.settimeout(min(gate.request_timeout, remaining))
                    body = self.rfile.read(length)
                    payload = json.loads(body)
                    allowance = gate.ledger.allowances[parts[1]]
                    tokens = payload.get("max_tokens")
                    if (
                        payload.get("model") != gate.model
                        or type(tokens) is not int
                        or not 1 <= tokens <= allowance.output_tokens
                    ):
                        raise ValueError
                    if gate.chat_template_kwargs:
                        supplied = payload.get("chat_template_kwargs", {})
                        if not isinstance(supplied, dict) or any(
                            key in supplied and supplied[key] != value
                            for key, value in gate.chat_template_kwargs.items()
                        ):
                            raise ValueError
                        payload["chat_template_kwargs"] = supplied | gate.chat_template_kwargs
                        body = json.dumps(payload).encode()
                    response_format = payload.get("response_format")
                    if (
                        gate.structured_output_mode == "json_object"
                        and isinstance(response_format, dict)
                        and response_format.get("type") == "json_schema"
                    ):
                        schema = response_format["json_schema"]["schema"]
                        payload["messages"] = [
                            *payload["messages"],
                            {
                                "role": "system",
                                "content": "Return one JSON object without Markdown fences, "
                                "satisfying this JSON Schema. Encode string newlines, tabs, "
                                "quotes and backslashes using valid JSON escapes.\n"
                                + json.dumps(schema),
                            },
                        ]
                        payload["response_format"] = {"type": "json_object"}
                        body = json.dumps(payload).encode()
                except (ValueError, TypeError, AttributeError, KeyError, TimeoutError):
                    return self.reject(400, "Invalid model request or output-token bound")
                try:
                    call_id = gate.ledger.claim(parts[1], body)
                except RuntimeError:
                    return self.reject(429, "Request allowance exhausted")
                connection_type = (
                    http.client.HTTPSConnection
                    if gate.route.scheme == "https"
                    else http.client.HTTPConnection
                )
                assert gate.route.hostname is not None
                upstream = connection_type(
                    gate.route.hostname,
                    gate.route.port,
                    timeout=min(gate.request_timeout, remaining),
                )
                started = False
                try:
                    upstream.request(
                        "POST",
                        gate.route.path.rstrip("/") + "/chat/completions",
                        body=body,
                        headers={
                            "Authorization": "Bearer " + gate.credential,
                            "Content-Type": "application/json",
                        },
                    )
                    response = upstream.getresponse()
                    if 300 <= response.status < 400:
                        gate.ledger.finish(call_id, "redirect_rejected")
                        return self.reject(502, "Inference redirects are unsupported")
                    self.send_response(response.status)
                    self.send_header(
                        "Content-Type", response.getheader("Content-Type", "application/json")
                    )
                    self.send_header("Connection", "close")
                    self.end_headers()
                    started = True
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    gate.ledger.finish(call_id, f"http_{response.status}")
                except (OSError, http.client.HTTPException):
                    # An uncertain request keeps its consumed slot. No retry here.
                    if not started:
                        self.reject(502, "Inference transport failed; request counted")
                finally:
                    upstream.close()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.block_on_close = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> InferenceGate:
        self.thread.start()
        return self

    def endpoint(self, scope: str) -> str:
        if scope not in self.ledger.allowances:
            raise ValueError("Unknown request scope")
        return f"http://127.0.0.1:{self.server.server_port}/{scope}/v1"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
