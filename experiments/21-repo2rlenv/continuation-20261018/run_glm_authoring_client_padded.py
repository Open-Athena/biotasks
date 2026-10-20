"""Generation-only transport variant with bounded JSON-whitespace keepalive.

The native request and successful upstream JSON bytes are unchanged. HTTP status
must be committed before inference finishes: later upstream failures therefore
produce an error object with no choices, never a fabricated model answer. Exact
upstream status/content are archived separately. No target code runs here.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from uuid import uuid4

import httpx
from glm_generation_transport_contract import (
    MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES, Server, registration_address,
    transport_check, validate_author_request,
)

INTERVAL = 30
DEADLINE = 1200
CHUNK = b" " * 4096
# Fixed length preserves the already tested proxy behavior without chunked HTTP.
# Trailing JSON whitespace fills the unused allowance; model fields are untouched.
PADDED_BYTES = MAX_RESPONSE_BYTES + (DEADLINE // INTERVAL + 2) * len(CHUNK)
FAILURE = b'{"error":{"type":"inference_transport_failed","message":"Inspect the preserved upstream receipt; no completion was delivered."}}'


async def upstream_response(method, url, body, key):
    """Enforce a wall deadline, including streaming reads, without a retry."""
    async with asyncio.timeout(DEADLINE):
        async with httpx.AsyncClient(timeout=httpx.Timeout(DEADLINE, connect=30),
                                     follow_redirects=False) as client:
            async with client.stream(method, url, headers={
                "Authorization": "Bearer " + key, "Content-Type": "application/json",
            }, content=body or None) as response:
                blocks = []
                size = 0
                async for block in response.aiter_bytes():
                    size += len(block)
                    if size > MAX_RESPONSE_BYTES:
                        raise ValueError("Response exceeds existing capture bound")
                    blocks.append(block)
                return response.status_code, b"".join(blocks)


def padded_reply(handler, fetch, row):
    """Keep a complete JSON response readable while preserving exact answer bytes."""
    completed = threading.Event()
    result = {}

    def work():
        try:
            content = fetch()
            if len(content) > MAX_RESPONSE_BYTES:
                raise ValueError("Oversize response")
            result["content"] = content
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            result["content"] = FAILURE
        finally:
            completed.set()

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    sent = 0
    disconnected = False
    started = time.monotonic()
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(PADDED_BYTES))
        handler.end_headers()
        while True:
            try:
                if not disconnected:
                    handler.wfile.write(CHUNK)
                    handler.wfile.flush()
                    sent += len(CHUNK)
            except OSError:
                disconnected = True
                row["caller_disconnected"] = True
            if completed.wait(INTERVAL):
                break
            if time.monotonic() - started > DEADLINE + INTERVAL:
                # The async upstream deadline should finish first. Keep the gate
                # held until it does; never start another uncertain model call.
                raise TimeoutError("Upstream worker did not honor wall deadline")
        content = result["content"]
        if not disconnected:
            handler.wfile.write(content)
            remaining = PADDED_BYTES - sent - len(content)
            assert remaining >= 0
            while remaining:
                chunk = CHUNK[:min(remaining, len(CHUNK))]
                handler.wfile.write(chunk)
                remaining -= len(chunk)
            handler.wfile.flush()
        row.update(padded_response_bytes=PADDED_BYTES,
                   leading_whitespace_bytes=sent,
                   payload_sha256=hashlib.sha256(content).hexdigest())
    finally:
        # async cancellation closes its HTTP client on timeout. Do not silently
        # release concurrency while a request is still executing.
        worker.join(DEADLINE + INTERVAL)
        if worker.is_alive():
            raise RuntimeError("Uncertain upstream worker still active")


def main():
    from iris.client.client import iris_ctx
    from iris.cluster.client.job_info import get_job_info
    from iris.cluster.types import EndpointAccess, JobName

    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    if os.environ.get("DAYTONA_API_KEY") or os.environ.get("REPO2RLENV_REMOTE_WORKER"):
        raise RuntimeError("Inference-only client cannot receive sandbox credentials")
    diagnostic = os.environ.get("BIOTASKS21_TRANSPORT_ONLY") == "1"
    token = os.environ["BIOTASKS21_INFERENCE_CLIENT_TOKEN"]
    assert len(token) >= 32
    key = "" if diagnostic else os.environ["BIOTASKS21_GLM_KEY"]
    delay = int(os.environ.get("BIOTASKS21_DIAGNOSTIC_DELAY_SECONDS", "650"))
    lifetime = int(os.environ.get("BIOTASKS21_CLIENT_LIFETIME_SECONDS", "7200"))
    assert delay in (130, 650) and 900 <= lifetime <= 7200
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    ctx = iris_ctx()
    info = get_job_info()
    assert info is not None
    upstream = None
    if not diagnostic:
        found = ctx.client.resolver_for_job(JobName.from_string(os.environ["BIOTASKS21_GLM_RELAY_JOB"])).resolve("glm-5.3")
        assert found.endpoints
        upstream = found.endpoints[0].url.rstrip("/")
        if not upstream.endswith("/v1"):
            upstream += "/v1"
    lock = threading.Lock()
    gate = threading.BoundedSemaphore(1)
    consumed = set()
    stop = threading.Event()
    started = time.monotonic()

    def append(row):
        with lock, (output / "inference-usage.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, content):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def dispatch(self):
            if not hmac.compare_digest(self.headers.get("X-Biotasks21-Inference-Token", "").encode(), token.encode()):
                self.reply(401, b'{"error":"unauthorized"}')
                return
            allowed = {( "GET", "/v1/models"), *( ("POST", path) for path in (
                "/v1/chat/completions", "/v1/transport-check", "/v1/transport-delay-check", "/v1/finish",
                "/v1/diagnostic/chat/completions", "/v1/diagnostic-error/chat/completions"))}
            if (self.command, self.path) not in allowed:
                self.reply(404, b'{"error":"unsupported_route"}')
                return
            raw = b""
            if self.command == "POST":
                try:
                    size = int(self.headers.get("Content-Length", "-1"))
                    if not 0 < size <= MAX_REQUEST_BYTES:
                        raise ValueError("Bounded request required")
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError("Incomplete request")
                    payload = validate_author_request(raw)
                except (ValueError, TypeError):
                    self.reply(400, b'{"error":"invalid_native_request"}')
                    return
            digest = hashlib.sha256(raw).hexdigest()
            if self.path == "/v1/transport-check":
                self.reply(200, json.dumps(transport_check(raw)).encode())
                return
            if not gate.acquire(blocking=False):
                self.reply(429, b'{"error":"inference_client_busy"}')
                return
            row = {"stage": "inference_only_padded_transport", "method": self.command,
                   "request_sha256": digest, "repository_execution": False, "model_calls": 0}
            request_started = time.monotonic()
            request_receipt = None
            try:
                if self.path == "/v1/finish":
                    append({"stage": "authenticated_finish", "model_calls": 0})
                    self.reply(200, b'{"stage":"finishing","model_calls":0}')
                    stop.set()
                    return
                if self.path in ("/v1/transport-delay-check", "/v1/diagnostic/chat/completions",
                                 "/v1/diagnostic-error/chat/completions"):
                    result = dict(transport_check(raw), diagnostic_delay_seconds=delay,
                                  padded_transport=True, padded_response_bytes=PADDED_BYTES)
                    def delayed():
                        if self.path == "/v1/diagnostic-error/chat/completions":
                            raise RuntimeError("Synthetic upstream failure; zero model calls")
                        time.sleep(delay)
                        row.update(model_calls=0, diagnostic_delay_seconds=delay)
                        if self.path == "/v1/diagnostic/chat/completions":
                            return json.dumps({"id": "synthetic-diagnostic-only", "object": "chat.completion",
                                "created": 0, "model": "glm-5.3", "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": json.dumps(result)}}],
                                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}).encode()
                        return json.dumps(result).encode()
                    padded_reply(self, delayed, row)
                    return
                if diagnostic:
                    self.reply(403, b'{"error":"transport_diagnostic_only"}')
                    return
                if self.path == "/v1/chat/completions":
                    if stop.is_set():
                        self.reply(503, b'{"error":"inference_client_stopping"}')
                        return
                    if digest in consumed:
                        self.reply(409, b'{"error":"consumed_request_not_replayed"}')
                        row.update(model_calls=0, duplicate_request_rejected=True)
                        return
                    if lifetime - (time.monotonic() - started) < DEADLINE + 30:
                        self.reply(503, b'{"error":"insufficient_finite_client_lifetime"}')
                        row["model_calls"] = 0
                        return
                    consumed.add(digest)
                    row.update(model_calls=1, requested_max_tokens=payload.get("max_tokens", payload.get("max_completion_tokens")),
                               requested_effort="medium")
                    directory = output / "requests"
                    directory.mkdir(exist_ok=True)
                    request_file = directory / (digest + ".json")
                    with request_file.open("xb") as stream:
                        stream.write(raw)
                    request_file.chmod(0o600)
                    request_receipt = directory / (digest + "-receipt.json")
                    request_receipt.write_text(json.dumps(dict(row, status="dispatched")) + "\n")
                    request_receipt.chmod(0o600)

                def fetch():
                    status, content = asyncio.run(upstream_response(self.command,
                        upstream + self.path.removeprefix("/v1"), raw, key))
                    directory = output / "responses"
                    directory.mkdir(exist_ok=True)
                    path = directory / (digest + "-" + uuid4().hex + ".json")
                    path.write_bytes(content)
                    path.chmod(0o600)
                    row.update(upstream_status=status, response_file="responses/" + path.name,
                               response_bytes=len(content), response_sha256=hashlib.sha256(content).hexdigest())
                    if not 200 <= status < 300:
                        raise RuntimeError("Upstream returned failure; raw status preserved")
                    data = json.loads(content)
                    if self.path == "/v1/chat/completions":
                        if not data.get("choices"):
                            raise ValueError("Missing completion choices")
                        row.update(usage=data.get("usage"), finish_reasons=[choice.get("finish_reason") for choice in data["choices"]])
                    return content

                if self.path == "/v1/chat/completions":
                    padded_reply(self, fetch, row)
                else:
                    self.reply(200, fetch())
            except Exception as exc:
                row["handler_error_type"] = type(exc).__name__
                if isinstance(exc, (RuntimeError, TimeoutError)):
                    stop.set()
                # A partially committed response must not be followed by a
                # second HTTP response or a generated replacement completion.
            finally:
                row["elapsed_seconds"] = round(time.monotonic() - request_started, 3)
                if request_receipt is not None:
                    request_receipt.write_text(json.dumps(dict(row, status=(
                        "response_captured" if row.get("response_file") else "failed_or_uncertain"))) + "\n")
                append(row)
                gate.release()

        do_GET = dispatch
        do_POST = dispatch

    server = Server(("0.0.0.0", ctx.get_port("inference")), Handler)
    server.timeout = 2
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *args: stop.set())
    status = {"stage": "finite_inference_only_padded_JSON_transport_variant",
              "transport_diagnostic_only": diagnostic, "model": "existing_free_glm_5_3",
              "repository_execution": False, "sandbox_credentials_supplied": False,
              "upstream_service_modified": False, "lifetime_sec": lifetime,
              "upstream_wall_timeout_sec": DEADLINE, "padded_response_bytes": PADDED_BYTES,
              "maximum_concurrent_forwarded_requests": 1,
              "upstream_error_policy": "Preserved original error; padded HTTP200 contains error object, no choices or fabricated answer."}
    try:
        with ctx.registry.registered("inference", registration_address(info.advertise_host, server),
            {"purpose": "issue21_padded_generation_transport", "proxy_timeout_seconds": "1320"},
            access=EndpointAccess.ENDPOINT_ACCESS_LINK):
            status["status"] = "serving"
            (output / "client-status.json").write_text(json.dumps(status, indent=2) + "\n")
            while not stop.is_set() and time.monotonic() - started < lifetime:
                server.handle_request()
    finally:
        server.server_close()
        status.update(status="stopped", elapsed_seconds=round(time.monotonic() - started, 3))
        (output / "client-status.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    main()
