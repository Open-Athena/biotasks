"""Actual pinned SDK serialization with a mocked transport receipt; no network."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

from run_generation_sdk_transport_probe import checking_send, probe


def main():
    base = 'https://example.invalid/opaque-owned-route'
    token = 'synthetic-generation-wire-authentication'
    forwarded = []

    def receipt(client, request, *args, **kwargs):
        assert str(request.url) == base + '/v1/transport-check'
        raw = request.read()
        forwarded.append(json.loads(raw))
        return httpx.Response(200, request=request, json={
            'stage': 'authenticated_body_transport_check', 'model_calls': 0,
            'request_sha256': hashlib.sha256(raw).hexdigest(), 'request_bytes': len(raw)})

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        with patch.dict(os.environ, {'BIOTASKS21_INFERENCE_CLIENT_URL': base,
                                    'BIOTASKS21_GENERATION_CLIENT_TOKEN': token}), \
                patch.object(httpx.Client, 'send', new=receipt):
            assert probe(output) == 0
        result = json.loads((output / 'generation-sdk-probe.json').read_text())
        assert result['passed'] and result['model_calls'] == 0
        assert result['transport_requests'] == 1 and len(forwarded) == 1
        assert forwarded[0]['max_tokens'] == 131072
        assert forwarded[0]['chat_template_kwargs']['reasoning_effort'] == 'medium'
        assert forwarded[0]['response_format']['type'] == 'json_schema'
        assert token not in json.dumps(forwarded[0])

    record = {'transport_requests': 0}
    checking = checking_send(receipt, record, token, base)
    bad = httpx.Request('POST', base + '/v1/chat/completions', json={})
    try:
        checking(None, bad)
    except ValueError:
        pass
    else:
        raise AssertionError('A live completion route must never be forwarded')
    assert record['transport_requests'] == 0
    print(json.dumps({'stage': 'actual_pinned_SDK_wire_fixture_passed',
                      'live_network_requests': 0, 'model_calls': 0,
                      'captured_SDK_requests': 1,
                      'direct_completion_route_rejected_before_send': True,
                      'versions': result['versions']}))


if __name__ == '__main__':
    main()
