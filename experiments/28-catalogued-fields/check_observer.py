"""Guard/metadata fixtures: unchanged calls, actual billing, redaction and fail-closed."""

from decimal import Decimal
import gzip
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from observed_cli import Recorder
from provider_usage import charge


def response(cost, identifier='gen-fixture'):
    usage = {'prompt_tokens': 10, 'completion_tokens': 2}
    if cost is not None:
        usage['cost'] = cost
    return SimpleNamespace(id=identifier, model='fixture', usage=usage)


with TemporaryDirectory() as temporary:
    base = Path(temporary)
    with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'secret-fixture-value'}):
        recorder = Recorder(base / 'normal')
    sent = {'model': 'openrouter/fixture', 'messages': [{'role': 'user', 'content': 'secret-fixture-value'}],
            'max_tokens': 2048, 'temperature': 0.2, 'api_key': 'secret-fixture-value'}
    value = response('2.51')
    calls = []

    def original(**kwargs):
        assert kwargs == sent
        assert kwargs['messages'] is sent['messages']
        calls.append(kwargs)
        return value

    observed = recorder.completion(original)
    assert observed(**sent) is value
    assert observed(**sent) is value
    assert recorder.actual_cost == Decimal('5.02')
    try:
        observed(**sent)
        raise AssertionError('Budget failed to stop call')
    except RuntimeError:
        pass
    assert len(calls) == 2
    assert sent['api_key'] == 'secret-fixture-value'
    saved = gzip.open(base / 'normal/request-001.json.gz', 'rt').read()
    assert 'secret-fixture-value' not in saved and 'api_key' not in saved
    assert json.loads((base / 'normal/billing.json').read_text())['cost_complete']

    recorder = Recorder(base / 'lookup')
    value = response(None)
    with patch('observed_cli.generation', return_value={'id': value.id, 'total_cost': '0.19'}) as lookup:
        assert recorder.completion(lambda **_: value)(model='fixture') is value
    lookup.assert_called_once_with(value.id)
    assert recorder.actual_cost == Decimal('0.19')

    recorder = Recorder(base / 'unknown')
    with patch('observed_cli.generation', side_effect=ValueError('missing')):
        assert recorder.completion(lambda **_: value)(model='fixture') is value
    assert recorder.cost_unknown
    try:
        recorder.completion(lambda **_: (_ for _ in ()).throw(AssertionError('must not dispatch')))(model='fixture')
        raise AssertionError('Unknown cost must stop new calls')
    except RuntimeError:
        pass

    recorder = Recorder(base / 'exception')
    error = ValueError('same object')

    def failed(**_):
        raise error

    try:
        recorder.completion(failed)(model='fixture')
    except ValueError as observed_error:
        assert observed_error is error
    else:
        raise AssertionError('Original exception was swallowed')
    assert recorder.cost_unknown

assert charge(None) is None and charge(True) is None and charge('NaN') is None
assert charge('-1') is None and charge('Infinity') is None and charge('n/a') is None
assert charge(0) == Decimal('0')
print('Observer fixtures passed: one unchanged dispatch, same response/exception, actual-cost stop, metadata-only lookup, secret redaction.')
