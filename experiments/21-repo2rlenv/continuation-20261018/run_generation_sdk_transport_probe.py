"""Verify actual synchronous SDK serialization through the zero-model endpoint.

The SDK base URL contains a transport-check trap. The HTTP hook accepts only
that trap's completion suffix, rewrites it to transport-check, and stops after
verifying its receipt. No chat-completion route is forwarded to the service.
"""

import hashlib
import importlib.metadata
import json
import logging
import os
import platform
import subprocess
import tarfile
import time
from pathlib import Path
from unittest.mock import patch

import httpx


class BodyVerified(BaseException):
    """Stop the SDK after byte verification, before model-response parsing."""


def checking_send(original, record, token, base):
    trap = base.rstrip('/') + '/v1/transport-check/'

    def send(client, request, *args, **kwargs):
        if (request.method != 'POST' or not str(request.url).startswith(trap)
                or not request.url.path.endswith('/transport-check/chat/completions')):
            raise ValueError('Unexpected SDK destination; no request forwarded')
        if record['transport_requests'] != 0:
            raise ValueError('Only one zero-model SDK request is allowed')
        raw = request.read()
        payload = json.loads(raw)
        if (payload.get('model') != 'glm-5.3' or payload.get('max_tokens') != 131072
                or payload.get('chat_template_kwargs', {}).get('reasoning_effort') != 'medium'):
            raise ValueError('Native SDK generation settings changed')
        if request.headers.get('X-Biotasks21-Inference-Token') != token or token.encode() in raw:
            raise ValueError('Native SDK transport credential placement changed')
        request.url = request.url.copy_with(path=request.url.path[:-len('/chat/completions')])
        if str(request.url) != base.rstrip('/') + '/v1/transport-check':
            raise ValueError('Diagnostic must use only the zero-model endpoint')
        record['transport_requests'] += 1
        response = original(client, request, *args, **kwargs)
        response.read()
        receipt = response.json()
        response.close()
        if (response.status_code != 200 or receipt.get('model_calls') != 0
                or receipt.get('request_sha256') != hashlib.sha256(raw).hexdigest()
                or receipt.get('request_bytes') != len(raw)):
            raise ValueError('Zero-model SDK body receipt failed')
        record.update(body_sha256=receipt['request_sha256'], body_bytes=len(raw),
                      application_header_verified=True, token_absent_from_body=True,
                      requested_effort='medium', requested_max_output_tokens=131072,
                      transport_receipt=receipt, passed=True)
        raise BodyVerified()

    return send


def probe(output):
    from glm_authoring_adapter import adapted_authoring
    from repo2rlenv.campaigns.budget import BudgetLedger
    from repo2rlenv.pipelines.recipes.history import pipeline as history
    from repo2rlenv.spec.input import LLMSpec

    assert not os.environ.get('DAYTONA_API_KEY')
    base = os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/')
    token = os.environ['BIOTASKS21_GENERATION_CLIENT_TOKEN']
    settings = json.loads(Path('glm-generation-adaptation.json').read_text())
    assert settings['stage'] == 'generation_only' and not settings['paid_fallback']
    assert (settings['max_output_tokens'], settings['reasoning_effort'],
            settings['request_timeout_sec']) == (131072, 'medium', 1200)
    record = {'stage': 'actual_native_generation_SDK_body_transport_check',
              'model_calls': 0, 'model_responses': 0, 'task_attempts': 0,
              'transport_requests': 0, 'passed': False,
              'python_version': platform.python_version(),
              'versions': {name: importlib.metadata.version(name)
                           for name in ('litellm', 'openai', 'httpx')},
              'limits': ['SDK parsing of a genuine model response is not tested.',
                         'Native diagnostic dispatched receipt is not an inference call.']}
    model = LLMSpec(provider='openai', model='glm-5.3',
                    endpoint=base + '/v1/transport-check',
                    api_key_env='BIOTASKS21_GENERATION_CLIENT_TOKEN',
                    max_concurrent=1, timeout_sec=1200, fallback=None)
    ledger = BudgetLedger(output / 'native-diagnostic-budget.sqlite', limit_usd='1')
    try:
        with patch.object(httpx.Client, 'send', new=checking_send(httpx.Client.send, record, token, base)):
            with adapted_authoring(settings, output, metering_target='history'):
                history.metered_complete(
                    model, ledger=ledger, operation_id='zero-model-generation-sdk-body',
                    reservation_usd='.75', receipt=output / 'native-diagnostic-request.json',
                    system='Synthetic request serialization check only.',
                    user='Verify this synthetic body without model generation.',
                    max_tokens=5000, resume=False,
                    response_schema={'type': 'object', 'properties': {'ok': {'type': 'boolean'}},
                                     'required': ['ok'], 'additionalProperties': False})
    except BodyVerified:
        record['status'] = 'native_SDK_body_verified_no_generation'
    except Exception as exc:
        record.update(status='native_SDK_transport_failed', error_type=type(exc).__name__)
    (output / 'generation-sdk-probe.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record['passed'] else 1


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    if os.environ.get('BIOTASKS21_GENERATION_SDK_CHILD') == '1':
        logging.disable(logging.CRITICAL)
        return probe(output)
    started = time.monotonic()
    status = {'stage': 'native_generation_SDK_setup', 'model_calls': 0}
    try:
        source = Path('repo2rlenv-source.tar.gz')
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(source) as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP='True',
                   BIOTASKS21_GENERATION_SDK_CHILD='1')
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        with (output / 'private-runtime.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'mutation',
                            '--extra', 'harbor', '--extra', 'daytona', '--python', '3.12.3',
                            '--project', str(root)], env=env, stdout=log, stderr=log,
                           timeout=600, check=True)
            result = subprocess.run([str(root / '.venv/bin/python'), __file__], env=env,
                                    stdout=log, stderr=log, timeout=150)
        status.update(status='completed' if result.returncode == 0 else 'failed',
                      child_exit_code=result.returncode)
        return result.returncode
    except Exception as exc:
        status.update(status='setup_failed', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
