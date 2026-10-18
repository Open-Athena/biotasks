"""Check our authenticated inference client from TRC, without generation."""

import hashlib
import json
import logging
import os
from pathlib import Path

import httpx


def main():
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.WARNING)
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    record = {'stage': 'zero_model_TRC_to_own_inference_client_preflight', 'model_calls': 0, 'repository_execution': False, 'sandbox_credentials_supplied': False, 'checks': []}
    try:
        assert not os.environ.get('DAYTONA_API_KEY')
        base = os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/')
        token = os.environ['BIOTASKS21_INFERENCE_CLIENT_TOKEN']
        payload = {'model': 'glm-5.3', 'max_tokens': 2048, 'messages': [{'role': 'user', 'content': 'Synthetic body transport check. ' * 64}]}
        raw = json.dumps(payload).encode()
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            missing = client.post(base + '/v1/transport-check', content=raw)
            record['checks'].append({'case': 'missing_application_bearer', 'status': missing.status_code, 'passed': missing.status_code == 401})
            invalid = client.post(base + '/v1/transport-check', json={**payload, 'max_tokens': 131072}, headers=headers)
            record['checks'].append({'case': 'authoring_allowance_rejected', 'status': invalid.status_code, 'passed': invalid.status_code == 400})
            valid = client.post(base + '/v1/transport-check', content=raw, headers=headers)
            data = valid.json()
            passed = valid.status_code == 200 and data.get('model_calls') == 0 and data.get('request_sha256') == hashlib.sha256(raw).hexdigest() and data.get('request_bytes') == len(raw)
            record['checks'].append({'case': 'native_body_length_and_hash_preserved', 'status': valid.status_code, 'passed': passed})
            models = client.get(base + '/v1/models', headers=headers)
            available = models.status_code == 200 and any(row.get('id') == 'glm-5.3' for row in models.json().get('data', []))
            record['checks'].append({'case': 'existing_approved_GLM_authenticated_discovery', 'status': models.status_code, 'passed': available})
        record['passed'] = all(row['passed'] for row in record['checks'])
    except Exception as exc:
        record.update(passed=False, error_type=type(exc).__name__)
    (output / 'transport-probe.json').write_text(json.dumps(record, indent=2) + '\n')
    # Never log request URLs, credentials, upstream model lists or raw errors.
    print(json.dumps(record), flush=True)
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
