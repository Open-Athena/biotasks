"""Check model-discovery failures without credentials or service calls."""
import httpx
from run_smith_author_trc import require_glm_model


def main():
    request = httpx.Request('GET', 'https://model.example/v1/models')
    cases = [(200, {'data': [{'id': 'glm-5.3'}]}, None), (200, {'data': [{'id': 'other'}]}, ValueError), (403, {}, httpx.HTTPStatusError)]
    for status, payload, failure in cases:
        response = httpx.Response(status, json=payload, request=request)
        try:
            require_glm_model(response)
        except Exception as exc:
            assert failure is not None and isinstance(exc, failure)
        else:
            assert failure is None
    print('Three model-discovery controls passed; no service calls or generation.')


if __name__ == '__main__':
    main()
