"""Exercise timeout metadata and durable response capture without live services."""
import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_glm_authoring_client_long_proxy as transport


class DisconnectedCaller(io.BytesIO):
    def write(self, value):
        raise BrokenPipeError('synthetic disconnected caller')


class LongProxyTransportTests(unittest.TestCase):
    def run_fixture(self, *, delayed=False, disconnected=False, transport_only=False,
                    delay_seconds=130, route=None):
        token = 'synthetic-application-token-1234567890'
        body = json.dumps({'model': 'glm-5.3', 'max_tokens': 131072,
            'chat_template_kwargs': {'reasoning_effort': 'medium'},
            'messages': [{'role': 'user', 'content': 'Synthetic fixture only.'}]}).encode()
        answer = b'{"choices":[{"finish_reason":"stop","message":{"content":"synthetic answer"}}],"usage":{"total_tokens":7}}'
        seen = {'upstream_calls': 0}
        signals = {}

        @contextmanager
        def registered(name, address, metadata, **kwargs):
            seen['metadata'] = metadata
            yield 'synthetic-endpoint'

        ctx = SimpleNamespace(get_port=lambda name: 0,
            registry=SimpleNamespace(registered=registered),
            client=SimpleNamespace(resolver_for_job=lambda job: SimpleNamespace(
                resolve=lambda name: SimpleNamespace(endpoints=[SimpleNamespace(url='http://fixture.invalid/v1')]))))

        class FakeClient:
            def __init__(self, **kwargs):
                seen['upstream_timeout'] = kwargs['timeout'].read

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            @contextmanager
            def stream(self, method, url, **kwargs):
                seen['upstream_calls'] += 1
                seen['request_body'] = kwargs['content']
                yield SimpleNamespace(status_code=200, is_success=True,
                    iter_bytes=lambda: iter([answer]))

        class FakeServer:
            def __init__(self, address, handler):
                self.server_address = ('127.0.0.1', 12345)
                self.handler = handler

            def handle_request(self):
                request = object.__new__(self.handler)
                request.headers = {'Content-Length': str(len(body)),
                    'X-Biotasks21-Inference-Token': token}
                request.command = 'POST'
                request.path = route or ('/v1/transport-delay-check' if delayed else '/v1/chat/completions')
                request.rfile = io.BytesIO(body)
                request.wfile = DisconnectedCaller() if disconnected else io.BytesIO()
                request.send_response = lambda value: seen.update(reply_status=value)
                request.send_header = lambda *args: None
                request.end_headers = lambda: None
                request.dispatch()
                seen['reply_body'] = request.wfile.getvalue()
                signals[transport.signal.SIGTERM](None, None)

            def server_close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            env = {'IRIS_OUTPUT_DIR': directory, 'BIOTASKS21_INFERENCE_CLIENT_TOKEN': token,
                   'BIOTASKS21_GLM_KEY': 'synthetic-upstream-key',
                   'BIOTASKS21_GLM_RELAY_JOB': '/fixture/relay', 'DAYTONA_API_KEY': '',
                   'REPO2RLENV_REMOTE_WORKER': '',
                   'BIOTASKS21_TRANSPORT_ONLY': '1' if transport_only else '0',
                   'BIOTASKS21_DIAGNOSTIC_DELAY_SECONDS': str(delay_seconds)}
            with patch.dict(os.environ, env), patch.object(transport, 'iris_ctx', return_value=ctx), \
                 patch.object(transport, 'get_job_info', return_value=SimpleNamespace(advertise_host='127.0.0.1')), \
                 patch.object(transport, 'Server', FakeServer), \
                 patch.object(transport.httpx, 'Client', FakeClient), \
                 patch.object(transport.signal, 'signal', side_effect=lambda sig, fn: signals.update({sig: fn})), \
                 patch.object(transport.time, 'sleep') as sleep:
                transport.main()
                seen['sleep_calls'] = [call.args for call in sleep.call_args_list]
            root = Path(directory)
            seen['rows'] = [json.loads(line) for line in (root / 'inference-usage.jsonl').read_text().splitlines()]
            seen['responses'] = [file.read_bytes() for file in (root / 'responses').glob('*')] if (root / 'responses').exists() else []
        return seen, body, answer

    def test_response_is_preserved_even_when_caller_disconnects(self):
        seen, body, answer = self.run_fixture(disconnected=True)
        self.assertEqual(seen['upstream_calls'], 1)
        self.assertEqual(seen['request_body'], body)
        self.assertEqual(seen['responses'], [answer])
        self.assertEqual(seen['rows'][0]['usage']['total_tokens'], 7)
        self.assertEqual(seen['rows'][0]['error_type'], 'BrokenPipeError')
        self.assertEqual(seen['metadata']['proxy_timeout_seconds'], '1320')
        self.assertEqual(seen['upstream_timeout'], 1200)

    def test_longer_diagnostic_and_finish_make_no_upstream_requests(self):
        seen, _, _ = self.run_fixture(delayed=True, transport_only=True, delay_seconds=650)
        self.assertEqual(seen['upstream_calls'], 0)
        self.assertEqual(seen['sleep_calls'], [(650,)])
        self.assertEqual(json.loads(seen['reply_body'])['model_calls'], 0)
        finished, _, _ = self.run_fixture(transport_only=True, route='/v1/finish')
        self.assertEqual(finished['upstream_calls'], 0)
        self.assertEqual(json.loads(finished['reply_body'])['stage'], 'finishing')

    def test_transport_only_client_cannot_forward_a_model_request(self):
        seen, _, _ = self.run_fixture(transport_only=True)
        self.assertEqual(seen['upstream_calls'], 0)
        self.assertEqual(seen['reply_status'], 403)

    def test_delayed_diagnostic_is_zero_model_and_has_timeout_metadata(self):
        seen, _, _ = self.run_fixture(delayed=True)
        self.assertEqual(seen['upstream_calls'], 0)
        self.assertEqual(seen['sleep_calls'], [(130,)])
        self.assertEqual(seen['responses'], [])
        self.assertEqual(json.loads(seen['reply_body'])['model_calls'], 0)
        self.assertEqual(json.loads(seen['reply_body'])['diagnostic_delay_seconds'], 130)
        self.assertEqual(seen['metadata']['proxy_timeout_seconds'], '1320')


if __name__ == '__main__':
    unittest.main()
