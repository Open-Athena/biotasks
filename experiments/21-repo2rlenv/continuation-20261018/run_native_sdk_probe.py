"""One synthetic request through the pinned Harbor SDK; never a task attempt."""

import asyncio
import contextlib
import datetime
import hashlib
import importlib.metadata
import json
import logging
import os
import subprocess
import tarfile
import time
from pathlib import Path


async def probe(output):
    import litellm
    from harbor.llms.lite_llm import LiteLLM
    from glm_solver_settings import ATTEMPT_TIMEOUT_SEC, MODEL
    from native_solver_transport import solver_transport_kwargs

    record = {'stage': 'single_synthetic_native_SDK_preflight', 'task_attempts': 0,
              'requests_dispatched': 0, 'responses_received': 0,
              'effort': 'unset_native', 'max_output_tokens': 2048,
              'status': 'started', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'versions': {name: importlib.metadata.version(name) for name in ('harbor', 'litellm', 'openai')}}
    token = os.environ['BIOTASKS21_INFERENCE_CLIENT_TOKEN']
    options = solver_transport_kwargs(os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/') + '/v1', token)
    os.environ['OPENAI_API_KEY'] = token
    assert importlib.metadata.version('harbor') == '0.22.0'
    assert options['max_turns'] == 12 and options['llm_call_kwargs']['max_tokens'] == 2048
    original = litellm.acompletion

    async def observed_completion(**kwargs):
        assert record['requests_dispatched'] == 0, 'Only one diagnostic request is authorized'
        assert kwargs['model'] == MODEL and kwargs['max_tokens'] == 2048
        assert kwargs['extra_headers']['X-Biotasks21-Inference-Token'] == token
        # Harbor explicitly supplies reasoning_effort=None for native/unset.
        # This is not an explicit model-effort setting; retain it unchanged.
        assert kwargs.get('reasoning_effort') is None
        assert not any(key in kwargs for key in ('thinking', 'chat_template_kwargs'))
        assert token not in json.dumps(kwargs['messages'])
        record.update(requests_dispatched=1, native_settings_verified=True,
                      custom_auth_header_present=True, token_absent_from_messages=True)
        # Diagnostic only: disable library retries so this cannot silently send
        # a second synthetic generation. Task solver settings stay untouched.
        response = await original(**kwargs, num_retries=0, timeout=850)
        safe = response.model_dump(mode='json')
        choice = safe['choices'][0]
        message = choice['message']
        record.update(responses_received=1, finish_reason=choice['finish_reason'],
                      usage=safe.get('usage'), answer_characters=len(message.get('content') or ''),
                      reasoning_characters=len(message.get('reasoning_content') or ''))
        (output / 'synthetic-response.json').write_text(json.dumps({
            'model': safe.get('model'), 'choices': safe['choices'], 'usage': safe.get('usage')}, indent=2) + '\n')
        return response

    litellm.acompletion = observed_completion
    try:
        llm = LiteLLM(model_name=MODEL, api_base=options['api_base'])
        response = await asyncio.wait_for(llm.call(
            'Reply with exactly OK. This is a synthetic connection test.',
            **options['llm_call_kwargs']), timeout=ATTEMPT_TIMEOUT_SEC)
        record.update(status='native_SDK_returned', native_SDK_passed=True)
    except Exception as exc:
        record.update(status='native_SDK_exception', error_type=type(exc).__name__, native_SDK_passed=False)
    finally:
        litellm.acompletion = original
        record['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / 'native-sdk-probe.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record.get('native_SDK_passed') else 1


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    if os.environ.get('BIOTASKS21_NATIVE_PROBE_CHILD') == '1':
        logging.disable(logging.CRITICAL)
        assert not os.environ.get('DAYTONA_API_KEY')
        return asyncio.run(probe(output))
    status = {'stage': 'native_SDK_environment_setup', 'task_attempts': 0, 'status': 'started'}
    started = time.monotonic()
    try:
        source = Path('repo2rlenv-source.tar.gz')
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(source) as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP='True')
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        # Raw setup/SDK diagnostics remain private pending explicit route and
        # credential review. Never print native SDK errors to controller logs.
        with (output / 'private-runtime.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor', '--extra', 'daytona',
                            '--python', '3.12.3', '--project', str(root)], env=env,
                           stdout=log, stderr=log, check=True, timeout=600)
            env['BIOTASKS21_NATIVE_PROBE_CHILD'] = '1'
            result = subprocess.run([str(root / '.venv/bin/python'), __file__], env=env,
                                    stdout=log, stderr=log, timeout=930)
        status.update(status='completed' if result.returncode == 0 else 'failed', child_exit_code=result.returncode)
        return result.returncode
    except Exception as exc:
        status.update(status='setup_or_controller_failure', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
