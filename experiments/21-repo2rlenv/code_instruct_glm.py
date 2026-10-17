"""Record native code-instruct author calls using approved free-GLM settings."""

from contextlib import contextmanager
from unittest.mock import patch

import litellm
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines import code_instruct


@contextmanager
def adapted_code_instruct_glm(settings, output):
    if settings['stage'] != 'generation_only' or settings['paid_fallback']:
        raise ValueError('Expected approved generation-only settings')
    original_complete = code_instruct.complete
    original_transport = litellm.completion
    count = 0

    def transport(*args, **kwargs):
        extra = dict(kwargs.get('extra_body') or {})
        template = dict(extra.get('chat_template_kwargs') or {})
        template['reasoning_effort'] = settings['reasoning_effort']
        extra['chat_template_kwargs'] = template
        kwargs['extra_body'] = extra
        response = original_transport(*args, **kwargs)
        choice = response.choices[0]
        save_record(output / f'call-{count:03d}.raw.json', {
            'finish_reason': choice.finish_reason,
            'content': choice.message.content,
            'reasoning_content': getattr(choice.message, 'reasoning_content', None),
            'usage': response.usage.model_dump(mode='json') if response.usage else None,
        })
        return response

    def complete(spec, **kwargs):
        nonlocal count
        if spec.model != settings['model'] or spec.provider != 'openai':
            raise ValueError('Unexpected model route')
        if not spec.endpoint or spec.fallback is not None:
            raise ValueError('Existing GLM endpoint without fallback required')
        if spec.timeout_sec != settings['request_timeout_sec']:
            raise ValueError('Unexpected request timeout')
        count += 1
        native_max_tokens = kwargs['max_tokens']
        kwargs['max_tokens'] = settings['max_output_tokens']
        request = {
            'stage': 'generation_only', 'status': 'dispatched',
            'model': spec.qualified_name,
            'system': kwargs.get('system'), 'user': kwargs['user'],
            'native_max_tokens': native_max_tokens,
            'max_tokens': kwargs['max_tokens'],
            'reasoning_effort': settings['reasoning_effort'],
            'timeout_sec': spec.timeout_sec,
        }
        path = output / f'call-{count:03d}.json'
        save_record(path, request)
        try:
            response = original_complete(spec, **kwargs)
        except Exception as exc:
            request.update(status='failed', error_type=type(exc).__name__)
            save_record(path, request)
            # The native caller logs exception messages; keep private routes out.
            raise RuntimeError(type(exc).__name__) from None
        request.update(status='returned', prompt_tokens=response.prompt_tokens,
                       completion_tokens=response.completion_tokens)
        save_record(path, request)
        return response

    with (
        patch.object(code_instruct, 'complete', complete),
        patch.object(litellm, 'completion', transport),
    ):
        yield
