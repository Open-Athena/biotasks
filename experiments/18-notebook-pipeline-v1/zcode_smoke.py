"""Bounded remote ZCode integration check; receives service access only at runtime."""

import base64
import gzip
import hashlib
import http.server
import json
import os
import signal
import subprocess
import tarfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from iris.client.client import iris_ctx
from iris.cluster.types import JobName


def main():
    root = Path.cwd()
    token = os.environ.pop('GLM_BULK_TOKEN')
    relay = os.environ.pop('GLM_ENDPOINT_JOB')
    upstream = iris_ctx().client.resolver_for_job(JobName.from_string(relay)).resolve(
        'glm-5.3').endpoints[0].url.rstrip('/')
    if not upstream.endswith('/v1'):
        upstream += '/v1'
    node_version = 'v24.14.0'
    archive_name = f'node-{node_version}-linux-x64.tar.xz'
    node_url = f'https://nodejs.org/dist/{node_version}/'
    archive = root / archive_name
    urllib.request.urlretrieve(node_url + archive_name, archive)
    expected = next(line.split()[0] for line in urllib.request.urlopen(
        node_url + 'SHASUMS256.txt', timeout=30).read().decode().splitlines()
        if line.split()[-1] == archive_name)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    with tarfile.open(archive) as src:
        src.extractall(root, filter='data')
    node = root / archive_name.removesuffix('.tar.xz') / 'bin/node'
    assert hashlib.sha256((root/'zcode.cjs').read_bytes()).hexdigest() == (
        'fad4c35c4c36ec210d8a06d3fa0e77de23c8545e2eb6ff90aea1eb38d1e6275f')
    requests = []
    mutex = threading.Lock()

    class Proxy(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != '/v1/chat/completions':
                self.send_error(403, 'Only chat completions are enabled')
                return
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with mutex:
                if len(requests) >= 4 or data.get('model') != 'glm-5.3':
                    self.send_error(403, 'Model or smoke request budget rejected')
                    return
                record = {'index': len(requests), 'model': data['model'],
                          'message_count': len(data.get('messages', [])),
                          'tool_count': len(data.get('tools', []))}
                requests.append(record)
            data.pop('max_completion_tokens', None)
            data['max_tokens'] = min(data.get('max_tokens') or 8192, 8192)
            record['max_tokens'] = data['max_tokens']
            start = time.monotonic()
            try:
                req = urllib.request.Request(upstream + '/chat/completions',
                    data=json.dumps(data).encode(), headers={
                        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=150) as response:
                    record['http_status'] = response.status
                    self.send_response(response.status)
                    self.send_header('Content-Type', response.headers.get('Content-Type'))
                    self.end_headers()
                    while chunk := response.read1(16384):
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except urllib.error.HTTPError as exc:
                record['http_status'] = exc.code
                self.send_error(502, 'Upstream rejected request')
            except Exception as exc:
                record['error_type'] = type(exc).__name__
            finally:
                record['elapsed_seconds'] = round(time.monotonic() - start, 3)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    workspace = root/'smoke-workspace'
    workspace.mkdir()
    state = root/'zcode-state'
    state.mkdir()
    config = {'features': {'mcp': False}, 'plugins': {'enabled': False},
              'memory': {'enabled': False}, 'skills': {'enabled': False},
              'toolConcurrency': {'maxConcurrency': 1}}
    user_config = Path.home()/'.zcode/cli/config.json'
    user_config.parent.mkdir(parents=True, exist_ok=True)
    # This runs only in a fresh disposable job container, never on the shared VM.
    user_config.write_text(json.dumps(config))
    personal = {'schemaVersion': 1, 'config': {
        'providerConfigRules': {'providerRules': [{
            'providerId': 'biotasks', 'providerName': 'BioTasks bounded service',
            'enabled': True, 'config': {'group': 'standard-personal',
                'access': {'type': 'api-key', 'apiKey': 'local-proxy'},
                'api': {'type': 'openai-chat-completions',
                        'baseUrl': f'http://127.0.0.1:{server.server_port}/v1'},
                'personalModelIds': ['glm-5.3']}}]},
        'modelConfigRules': {'manualProviderModelRules': [], 'providerModelRules': [{
            'providerId': 'biotasks', 'modelId': 'glm-5.3', 'config': {
                'enabled': True, 'properties': {'contextWindow': 131072},
                'optionSpecs': {'maxOutputTokens': {'max': 8192}}}}]},
        'defaultModelSelection': {'providerId': 'biotasks', 'modelId': 'glm-5.3',
                                 'options': {'reasoningLevel': 'low'}}}}
    (state/'provider.json').write_text(json.dumps(personal))
    env = os.environ | {
        'ZCODE_STORAGE_DIR': str(state/'cli'),
        'ZCODE_BUILTIN_PROVIDER_CONFIG_FILE': str(root/'zcode-builtin.json'),
        'ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE': str(root/'zcode-builtin.json'),
        'ZCODE_PERSONAL_PROVIDER_CONFIG_FILE': str(state/'provider.json'),
        'ZCODE_MAX_TOOL_CONCURRENCY': '1',
        'PATH': str(node.parent) + ':' + os.environ.get('PATH', '')}
    prompt = 'Write the exact text READY followed by a newline to readiness.txt in the current workspace. Then stop. Do not use other agents, web access or unrelated tools.'
    start = time.monotonic()
    with (root/'zcode-events.jsonl').open('wb') as out, (root/'zcode-stderr.txt').open('wb') as err:
        process = subprocess.Popen([str(node), str(root/'zcode.cjs'), '--cwd', str(workspace),
            '--prompt', prompt, '--output-format', 'stream-json', '--locale', 'en-US'],
            env=env, stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        try:
            process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    server.shutdown()
    marker = workspace/'readiness.txt'
    result = {'stage': 'harness_smoke', 'scientific_task': False,
              'zcode_cli_version': '0.16.9', 'release': '3.14.5',
              'exit_code': process.returncode, 'timed_out': timed_out,
              'elapsed_seconds': round(time.monotonic()-start, 3), 'requests': requests,
              'marker_matches': marker.exists() and marker.read_text() == 'READY\n'}
    artifacts = {'result.json': json.dumps(result),
                 'zcode-events.jsonl': (root/'zcode-events.jsonl').read_text(errors='replace'),
                 'zcode-stderr.txt': (root/'zcode-stderr.txt').read_text(errors='replace')}
    # Only explicitly selected artifacts; no provider config, environment or credentials.
    encoded = json.dumps(artifacts).replace(token, '[REDACTED]').replace(upstream, '[ENDPOINT]')
    print('BIOTASKS_SMOKE_RESULT ' + json.dumps(result), flush=True)
    packed = gzip.compress(encoded.encode())
    export = base64.b64encode(packed).decode()
    pieces = [export[i:i+6000] for i in range(0, len(export), 6000)]
    print('BIOTASKS_SMOKE_ARCHIVE ' + json.dumps({
        'chunks': len(pieces), 'sha256': hashlib.sha256(packed).hexdigest()}), flush=True)
    for index, piece in enumerate(pieces):
        print(f'BIOTASKS_SMOKE_CHUNK {index} {piece}', flush=True)


if __name__ == '__main__':
    main()
