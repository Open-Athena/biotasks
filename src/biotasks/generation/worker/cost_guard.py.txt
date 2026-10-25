"""Conservative campaign reservation using live public route prices; no model call."""

from decimal import Decimal, ROUND_CEILING
import json
import urllib.request

URL = 'https://openrouter.ai/api/v1/models/anthropic/claude-sonnet-4.6/endpoints'
KNOWN_PRICES = {'prompt', 'completion', 'request', 'web_search', 'input_cache_read',
    'input_cache_write', 'input_cache_write_1h', 'discount'}


def reservation(data, max_tokens):
    endpoints = data['data']['endpoints']
    assert endpoints and max_tokens == 2048
    bounds = []
    for route in endpoints:
        prices = route['pricing']
        assert set(prices) <= KNOWN_PRICES, 'Unknown charge field; do not dispatch'
        assert route['context_length'] > 0 and 'prompt' in prices and 'completion' in prices
        prompt = max(Decimal(prices.get(name, '0')) for name in
            ['prompt', 'input_cache_read', 'input_cache_write', 'input_cache_write_1h'])
        completion, request = Decimal(prices['completion']), Decimal(prices.get('request', '0'))
        assert all(x.is_finite() and x >= 0 for x in [prompt, completion, request])
        bounds.append(Decimal(route['context_length']) * prompt + max_tokens * completion + request)
    # Full advertised context at the highest listed cache-write rate, plus completion,
    # with 20% headroom and a cent-rounded fixed margin. Native calls have no paid tools.
    return (max(bounds) * Decimal('1.2') + Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_CEILING)


def wrap(recorder, observed_completion, remaining_at_repo_start, repo_prior):
    def checked(*args, **kwargs):
        if recorder.cost_unknown or recorder.actual_cost >= recorder.threshold:
            return observed_completion(*args, **kwargs)  # Preserve original stop event.
        assert not args
        assert kwargs['model'] == 'openrouter/anthropic/claude-sonnet-4.6'
        assert kwargs['max_tokens'] == 2048 and kwargs['num_retries'] == 0
        assert not any(kwargs.get(key) for key in ['tools', 'tool_choice', 'plugins', 'reasoning'])
        assert all(isinstance(row['content'], str) for row in kwargs['messages'])
        try:
            with urllib.request.urlopen(URL, timeout=30) as response:
                body = response.read(1024**2 + 1)
            assert len(body) <= 1024**2
            quote = json.loads(body)
            reserve = reservation(quote, kwargs['max_tokens'])
        except Exception as error:
            recorder.event('campaign_reservation_unavailable', exception_type=type(error).__name__)
            raise RuntimeError('Cannot reserve next request against campaign budget') from error
        available = remaining_at_repo_start - repo_prior - recorder.actual_cost
        recorder.save(f'cost-quote-{recorder.calls + 1:03d}.json', quote)
        recorder.event('campaign_cost_reservation', available_usd=str(available),
            reserved_usd=str(reserve), allowed=available >= reserve, public_source=URL)
        if available < reserve:
            raise RuntimeError('Campaign budget cannot reserve next upstream request')
        # Forward the same call once. Actual billing/reconciliation remains in original observer.
        return observed_completion(*args, **kwargs)
    return checked

