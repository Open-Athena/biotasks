"""Finite inference-only CPU client for native generation requests from TRC.

Registers this job's own authenticated Iris endpoint. It does not change the
upstream model service, execute target repositories, or hold sandbox credentials.
"""
import hashlib
import hmac
import json
import logging
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from iris.client.client import iris_ctx
from iris.cluster.client.job_info import get_job_info
from iris.cluster.types import EndpointAccess, JobName

MAX_REQUEST_BYTES = 4 * 1024**2
MAX_RESPONSE_BYTES = 8 * 1024**2


def validate_author_request(body):
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError('Expected an object request')
    if payload.get('model') != 'glm-5.3':
        raise ValueError('Only the existing approved GLM model is allowed')
    if payload.get('stream'):
        raise ValueError('This generation transport uses complete responses')
    limits = [payload[key] for key in ('max_tokens', 'max_completion_tokens') if key in payload]
    if not limits or not all(type(limit) is int and 0 < limit <= 131072 for limit in limits):
        raise ValueError('Generation output allowance must be explicit and at most131072')
    if not isinstance(payload.get('messages'), list) or not payload['messages']:
        raise ValueError('Expected native chat messages')
    nested = payload.get('chat_template_kwargs', {})
    if not isinstance(nested, dict):
        raise ValueError('Invalid generation template arguments')
    efforts = [value for value in (payload.get('reasoning_effort'), nested.get('reasoning_effort')) if value is not None]
    if not efforts or any(value != 'medium' for value in efforts):
        raise ValueError('Generation requires explicit approved medium effort')
    # Preserve the validated caller payload; native authoring repair bounds remain caller-owned.
    return payload


def transport_check(body):
    """Authenticate and check a native request body without calling a model."""
    validate_author_request(body)
    return {'stage': 'authenticated_body_transport_check', 'request_sha256': hashlib.sha256(body).hexdigest(), 'request_bytes': len(body), 'model_calls': 0, 'repository_execution': False}


def registration_address(host, server):
    # Named ports may request zero: register the OS-selected listening port,
    # following Iris's own worker-pool server pattern.
    port = int(server.server_address[1])
    if not 0 < port <= 65535:
        raise ValueError('A bound nonzero service port is required')
    formatted_host = '[' + host + ']' if ':' in host and not host.startswith('[') else host
    return f'http://{formatted_host}:{port}'


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 4


def main():
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.WARNING)
    if os.environ.get('DAYTONA_API_KEY') or os.environ.get('REPO2RLENV_REMOTE_WORKER'):
        raise RuntimeError('Inference-only client must not receive sandbox execution credentials')
    token = os.environ['BIOTASKS21_INFERENCE_CLIENT_TOKEN']
    if len(token) < 32:
        raise ValueError('Protected client credential required')
    glm_key = os.environ['BIOTASKS21_GLM_KEY']
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    ctx = iris_ctx()
    info = get_job_info()
    if info is None:
        raise RuntimeError('Expected authorized Iris job context')
    found = ctx.client.resolver_for_job(JobName.from_string(os.environ['BIOTASKS21_GLM_RELAY_JOB'])).resolve('glm-5.3')
    if not found.endpoints:
        raise RuntimeError('Existing GLM service is not registered')
    upstream = found.endpoints[0].url.rstrip('/')
    if not upstream.endswith('/v1'):
        upstream += '/v1'
    lock = threading.Lock()
    gate = threading.BoundedSemaphore(1)
    receipts = output / 'inference-usage.jsonl'
    started = time.monotonic()
    stop = threading.Event()

    def append(record):
        with lock, receipts.open('a') as stream:
            stream.write(json.dumps(record) + '\n')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # URLs and authorization material must not enter job logs.

        def reply(self, status, raw):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def dispatch(self):
            # Iris authenticates the capability URL and strips Authorization
            # before forwarding. Keep our separate application credential in a
            # nonreserved header that its documented proxy preserves.
            if not hmac.compare_digest(self.headers.get('X-Biotasks21-Inference-Token', '').encode(), token.encode()):
                self.reply(401, b'{"error":"unauthorized"}')
                return
            allowed = (self.command, self.path) in {('GET', '/v1/models'), ('POST', '/v1/chat/completions'), ('POST', '/v1/transport-check')}
            if not allowed:
                self.reply(404, b'{"error":"unsupported_route"}')
                return
            row = {'stage': 'inference_only', 'method': self.command, 'repository_execution': False}
            raw = b''
            if self.command == 'POST':
                try:
                    size = int(self.headers.get('Content-Length', '-1'))
                    if not 0 < size <= MAX_REQUEST_BYTES:
                        raise ValueError('Invalid bounded request size')
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError('Incomplete request')
                    payload = validate_author_request(raw)
                    row.update(request_sha256=hashlib.sha256(raw).hexdigest(), requested_max_tokens=payload.get('max_tokens', payload.get('max_completion_tokens')), requested_effort=payload.get('reasoning_effort', payload.get('chat_template_kwargs', {}).get('reasoning_effort')), requested_thinking=payload.get('thinking'))
                except (ValueError, TypeError):
                    self.reply(400, b'{"error":"invalid_native_generation_request"}')
                    return
            if self.path == '/v1/transport-check':
                result = transport_check(raw)
                append(result)
                self.reply(200, json.dumps(result).encode())
                return
            if not gate.acquire(blocking=False):
                self.reply(429, b'{"error":"inference_client_busy"}')
                return
            request_started = time.monotonic()
            try:
                with httpx.Client(timeout=httpx.Timeout(1200, connect=30), follow_redirects=False) as client:
                    with client.stream(self.command, upstream + self.path.removeprefix('/v1'), headers={'Authorization': 'Bearer ' + glm_key, 'Content-Type': 'application/json'}, content=raw or None) as response:
                        blocks = []
                        count = 0
                        for block in response.iter_bytes():
                            count += len(block)
                            if count > MAX_RESPONSE_BYTES:
                                raise ValueError('Response exceeds transport capture bound')
                            blocks.append(block)
                        content = b''.join(blocks)
                        row['upstream_status'] = response.status_code
                        if response.is_success:
                            data = json.loads(content)
                            row['usage'] = data.get('usage')
                            row['finish_reasons'] = [x.get('finish_reason') for x in data.get('choices', [])]
                            self.reply(response.status_code, content)
                        else:
                            # Retain status, never echo private upstream diagnostics/routes.
                            self.reply(response.status_code, b'{"error":"existing_GLM_service_request_failed"}')
            except Exception as exc:
                row['error_type'] = type(exc).__name__
                try:
                    self.reply(502, b'{"error":"inference_transport_failed"}')
                except OSError:
                    pass
            finally:
                row['elapsed_seconds'] = round(time.monotonic() - request_started, 3)
                append(row)
                gate.release()

        do_GET = dispatch
        do_POST = dispatch

    port = ctx.get_port('inference')
    server = Server(('0.0.0.0', port), Handler)
    server.timeout = 2

    def shutdown(signum, frame):
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown)
    status = {'stage': 'finite_authenticated_generation_inference_only_client', 'status': 'starting', 'model': 'existing_free_glm_5_3', 'CPU_cost_basis': 'user_allocated_free_CoreWeave', 'repository_execution': False, 'sandbox_credentials_supplied': False, 'maximum_concurrent_forwarded_requests': 1, 'generation_max_output_tokens': 131072, 'generation_effort': 'medium', 'upstream_request_timeout_sec': 1200, 'lifetime_sec': 7200, 'upstream_service_modified': False}
    try:
        with ctx.registry.registered('inference', registration_address(info.advertise_host, server), {'purpose': 'issue21_native_generation_inference_only'}, access=EndpointAccess.ENDPOINT_ACCESS_LINK):
            status['status'] = 'serving'
            status['registered_bound_port_nonzero'] = True
            (output / 'client-status.json').write_text(json.dumps(status, indent=2) + '\n')
            while not stop.is_set() and time.monotonic() - started < 7200:
                server.handle_request()
    finally:
        server.server_close()
        status.update(status='stopped', elapsed_seconds=round(time.monotonic() - started, 3))
        (output / 'client-status.json').write_text(json.dumps(status, indent=2) + '\n')


if __name__ == '__main__':
    main()
