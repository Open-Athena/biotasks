"""Per-generation actual charges; shared-key totals are never repo costs."""

from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request


def snapshot():
    request = urllib.request.Request('https://openrouter.ai/api/v1/key', headers={
        'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'],
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)['data']
    keys = ['limit', 'limit_remaining', 'limit_reset', 'usage', 'byok_usage',
            'usage_daily', 'usage_monthly', 'is_provisioning_key', 'is_management_key']
    return {'observed_at': time.time(), **{key: value.get(key) for key in keys}}


def charge(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() and result >= 0 else None


def generation(response_id):
    """Read billing metadata only, with bounded retries for delayed records."""
    if not response_id:
        raise ValueError('Missing generation ID')
    request = urllib.request.Request(
        'https://openrouter.ai/api/v1/generation?' + urllib.parse.urlencode({'id': response_id}),
        headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY']},
    )
    last = None
    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value = json.load(response)['data']
            assert value['id'] == response_id
            assert charge(value.get('total_cost')) is not None
            keys = ['id', 'model', 'provider_name', 'created_at', 'total_cost',
                    'tokens_prompt', 'tokens_completion', 'native_tokens_prompt',
                    'native_tokens_completion', 'native_tokens_cached', 'finish_reason',
                    'native_finish_reason', 'cancelled', 'is_byok']
            return {key: value.get(key) for key in keys}
        except Exception as error:
            last = error
    raise RuntimeError('Per-generation cost unavailable: ' + type(last).__name__) from None


def record(stage):
    value = snapshot()
    value['not_repository_cost'] = True
    target = Path('/work/evidence/provider-usage-' + stage + '.json')
    target.write_text(json.dumps(value, indent=2) + '\n')
    return value
