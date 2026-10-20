"""Frozen request contract shared by the new padded generation transport.

Copied unchanged from the prior experimental transport for a controlled variant.
"""
import hashlib
import json
from http.server import ThreadingHTTPServer

MAX_REQUEST_BYTES = 4 * 1024**2
MAX_RESPONSE_BYTES = 8 * 1024**2


def validate_author_request(body):
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError('Expected an object request')
    if payload.get('model') != 'glm-5.3':
        raise ValueError('Only the existing approved GLM model is allowed')
    if payload.get('stream'):
        raise ValueError('This generation transport uses complete responses')
    limits = [payload[key] for key in ('max_tokens', 'max_completion_tokens') if key in payload]
    if not limits or not all(type(limit) is int and 0 < limit <= 131072 for limit in limits):
        raise ValueError('Generation output allowance must be explicit and at most131072')
    if not isinstance(payload.get('messages'), list) or not payload['messages']:
        raise ValueError('Expected native chat messages')
    nested = payload.get('chat_template_kwargs', {})
    if not isinstance(nested, dict):
        raise ValueError('Invalid generation template arguments')
    efforts = [value for value in (payload.get('reasoning_effort'), nested.get('reasoning_effort')) if value is not None]
    if not efforts or any(value != 'medium' for value in efforts):
        raise ValueError('Generation requires explicit approved medium effort')
    # Preserve the validated caller payload; native authoring repair bounds remain caller-owned.
    return payload


def transport_check(body):
    """Authenticate and check a native request body without calling a model."""
    validate_author_request(body)
    return {'stage': 'authenticated_body_transport_check', 'request_sha256': hashlib.sha256(body).hexdigest(), 'request_bytes': len(body), 'model_calls': 0, 'repository_execution': False}


def registration_address(host, server):
    # Named ports may request zero: register the OS-selected listening port,
    # following Iris's own worker-pool server pattern.
    port = int(server.server_address[1])
    if not 0 < port <= 65535:
        raise ValueError('A bound nonzero service port is required')
    formatted_host = '[' + host + ']' if ':' in host and not host.startswith('[') else host
    return f'http://{formatted_host}:{port}'


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 4
