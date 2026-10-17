"""Offline check through the native completion client; no network or models."""

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import litellm
from litellm.types.utils import Usage
from code_instruct_glm import adapted_code_instruct_glm, code_instruct
from repo2rlenv.spec.input import LLMSpec
from repo2rlenv.execution.lifecycle import save_record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    settings = json.loads(Path(__file__).with_name('glm-generation-adaptation.json').read_text())
    spec = LLMSpec(provider='openai', model='glm-5.3', endpoint='https://example.invalid/v1',
                   api_key_env='BIOTASKS21_OFFLINE_KEY', timeout_sec=1200, fallback=None)
    calls = []

    def transport(**kwargs):
        assert kwargs['max_tokens'] == 131072
        assert kwargs['timeout'] == 1200 and kwargs['num_retries'] == 0
        assert kwargs['extra_body']['chat_template_kwargs']['reasoning_effort'] == 'medium'
        calls.append(True)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(
            content='fixture', reasoning_content='fixture reasoning'))],
            usage=Usage(prompt_tokens=3, completion_tokens=7, total_tokens=10))

    with (
        patch.dict(os.environ, {'BIOTASKS21_OFFLINE_KEY': 'offline-fixture'}),
        patch.object(litellm, 'completion', transport),
        patch.object(litellm, 'completion_cost', return_value=0),
        adapted_code_instruct_glm(settings, args.output / 'calls'),
    ):
        response = code_instruct.complete(spec, system='Synthetic fixture', user='Synthetic input',
                                          max_tokens=2048, temperature=0.7)
        assert response.content == 'fixture' and len(calls) == 1
        try:
            code_instruct.complete(spec.model_copy(update={'fallback': spec}),
                                    user='Must not dispatch', max_tokens=2048, temperature=0.7)
        except ValueError:
            pass
        else:
            raise AssertionError('Fallback must be rejected')
    assert len(calls) == 1
    request = json.loads((args.output / 'calls/call-001.json').read_text())
    assert request['native_max_tokens'] == 2048 and request['max_tokens'] == 131072
    assert 'endpoint' not in request and 'api_key' not in request
    save_record(args.output / 'checks.json', {'stage': 'offline_native_transport_check',
        'model_calls': 0, 'mock_transport_calls': 1, 'approved_wire_settings': True,
        'fallback_rejected': True, 'request_and_raw_response_preserved': True})
    print('Native transport fixture passed; zero model calls')


if __name__ == '__main__':
    main()
