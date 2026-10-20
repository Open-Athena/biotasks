"""One bounded authenticated synthetic delay request; no model generation."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    base = os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/')
    token = os.environ['BIOTASKS21_GENERATION_CLIENT_TOKEN']
    assert not os.environ.get('DAYTONA_API_KEY')
    delay = int(os.environ.get('BIOTASKS21_DIAGNOSTIC_DELAY_SECONDS', '130'))
    assert delay in (130, 650)
    timeout = 180 if delay == 130 else 780
    body = json.dumps({'model': 'glm-5.3', 'max_tokens': 131072,
        'chat_template_kwargs': {'reasoning_effort': 'medium'},
        'messages': [{'role': 'user', 'content': 'Synthetic delay receipt only; no model call.'}]}).encode()
    request = urllib.request.Request(base + '/v1/transport-delay-check', data=body,
        headers={'Content-Type': 'application/json', 'X-Biotasks21-Inference-Token': token})
    record = {'stage': 'authenticated_bounded_zero_model_proxy_probe',
        'model_calls': 0, 'task_attempts': 0, 'sandbox_provisioned': False,
        'requested_diagnostic_delay_seconds': delay, 'caller_timeout_seconds': timeout,
        'request_sha256': hashlib.sha256(body).hexdigest(), 'request_bytes': len(body),
        'passed': False}
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            record['http_status'] = response.status
            receipt = json.load(response)
        record['receipt'] = receipt
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        record['passed'] = (record['http_status'] == 200 and receipt['model_calls'] == 0
            and receipt['request_sha256'] == record['request_sha256']
            and receipt['diagnostic_delay_seconds'] == delay and record['elapsed_seconds'] >= delay - 5)
    except Exception as exc:
        record.update(error_type=type(exc).__name__, elapsed_seconds=round(time.monotonic() - started, 3))
        if isinstance(exc, urllib.error.HTTPError):
            record['http_status'] = exc.code
    finally:
        if os.environ.get('BIOTASKS21_FINISH_DIAGNOSTIC_CLIENT') == '1':
            finish = urllib.request.Request(base + '/v1/finish', data=body,
                headers={'Content-Type': 'application/json', 'X-Biotasks21-Inference-Token': token})
            try:
                with urllib.request.urlopen(finish, timeout=20) as response:
                    finished = json.load(response)
                    record['authenticated_finish_requested'] = (response.status == 200 and finished.get('stage') == 'finishing')
            except Exception as exc:
                record['finish_error_type'] = type(exc).__name__
    (output / 'proxy-delay-probe.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
