"""Scoped relay: capture requests and enforce the single paid judge call."""

import datetime
import json
import socket
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import httpx
import uvicorn
from iris.client.client import iris_ctx
from iris.cluster.client.job_info import get_job_info
from iris.cluster.types import EndpointAccess, PROXY_TIMEOUT_METADATA_KEY
from rigging.timing import Duration
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route


def model_app(base, key, judge_key, judge_token, output: Path, protocol):
    state = {}
    counters = {}

    @asynccontextmanager
    async def lifespan(_app):
        async with httpx.AsyncClient(timeout=httpx.Timeout(1800, connect=15)) as client:
            state['client'] = client
            yield

    async def completion(request):
        trial = request.path_params['trial']
        judge = trial == 'judge'
        if judge:
            if request.headers.get('authorization') != 'Bearer ' + judge_token:
                return JSONResponse({'error': 'Unauthorized'}, status_code=401)
        elif trial not in protocol['tasks']:
            return JSONResponse({'error': 'Unknown trial'}, status_code=404)
        payload = await request.json()
        expected = protocol['judge']['model'] if judge else 'glm-5.3'
        if payload.get('model') != expected:
            return JSONResponse({'error': 'Unexpected model'}, status_code=400)
        cap = payload.get('max_tokens', payload.get('max_completion_tokens'))
        if not isinstance(cap, int) or not 0 < cap <= (1024 if judge else 32768):
            return JSONResponse({'error': 'Unexpected output limit'}, status_code=400)
        limit = 1 if judge else protocol['solver_requests_per_task_cap']
        # No await between checking and incrementing: concurrent SDK retries
        # cannot reserve multiple paid calls. HTTPX itself has no retries.
        if counters.get(trial, 0) >= limit:
            return JSONResponse({'error': 'Authorized call budget exhausted'}, status_code=400)
        counters[trial] = counters.get(trial, 0) + 1
        if not judge:
            payload.update(protocol['sampling'])
        folder = output / 'model-requests' / trial
        folder.mkdir(parents=True, exist_ok=True)
        prefix = folder / f'request-{counters[trial]:05d}'
        prefix.with_suffix('.json').write_text(json.dumps(payload) + '\n')
        (output / 'request-counts.json').write_text(json.dumps(counters) + '\n')
        metadata = {'started_at': datetime.datetime.now(datetime.UTC).isoformat()}
        url = 'https://api.together.xyz/v1' if judge else base.rstrip('/')
        upstream_request = state['client'].build_request(
            'POST', url + '/chat/completions', json=payload,
            headers={'Authorization': 'Bearer ' + (judge_key if judge else key)},
        )
        try:
            upstream = await state['client'].send(upstream_request, stream=True)
        except httpx.HTTPError as error:
            metadata['error_type'] = type(error).__name__
            prefix.with_suffix('.metadata.json').write_text(json.dumps(metadata) + '\n')
            return JSONResponse({'error': 'Upstream request failed'}, status_code=502)
        metadata['http_status'] = upstream.status_code

        async def body():
            complete = False
            try:
                with prefix.with_suffix('.response').open('wb') as handle:
                    async for chunk in upstream.aiter_bytes():
                        handle.write(chunk)
                        yield chunk
                complete = True
            finally:
                await upstream.aclose()
                metadata.update(completed=complete, finished_at=datetime.datetime.now(datetime.UTC).isoformat())
                prefix.with_suffix('.metadata.json').write_text(json.dumps(metadata) + '\n')

        return StreamingResponse(body(), status_code=upstream.status_code,
                                 headers={'content-type': upstream.headers.get('content-type', 'application/json')})

    return Starlette(routes=[Route('/trial/{trial}/v1/chat/completions', completion, methods=['POST'])], lifespan=lifespan)


@contextmanager
def scoped_model_endpoint(base, key, judge_key, judge_token, output, protocol):
    info = get_job_info()
    if info is None:
        raise RuntimeError('Iris job metadata unavailable')
    ctx = iris_ctx()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((info.advertise_host, 0))
    server = uvicorn.Server(uvicorn.Config(model_app(base, key, judge_key, judge_token, output, protocol), log_level='warning', access_log=False))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Scoped relay startup failed')
            time.sleep(0.05)
        with ctx.registry.registered('model', f'http://{info.advertise_host}:{sock.getsockname()[1]}',
                                     {PROXY_TIMEOUT_METADATA_KEY: '1800'}, access=EndpointAccess.ENDPOINT_ACCESS_LINK):
            response = ctx.client.mint_endpoint_token(f'{ctx.namespace}/model', ttl=Duration.from_hours(4))
            if not response.capability_url:
                raise RuntimeError('Scoped relay registration failed')
            yield response.capability_url.rstrip('/')
    finally:
        server.should_exit = True
        thread.join(timeout=30)
        sock.close()
