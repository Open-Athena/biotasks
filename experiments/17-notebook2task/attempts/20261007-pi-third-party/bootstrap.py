"""Iris CPU orchestrator; service discovery stays in a private adapter."""

import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import zipfile

import httpx
from model_proxy import scoped_model_endpoint
from service_adapter import connect


protocol = json.loads(Path('protocol.json').read_text())
output = Path(os.environ['IRIS_OUTPUT_DIR'])
output.mkdir(parents=True, exist_ok=True)
for name in ['protocol.json', 'task-manifest.json', 'collect.py', 'bootstrap.py', 'model_proxy.py']:
    shutil.copyfile(name, output / name)
with zipfile.ZipFile('tasks.zip') as archive:
    archive.extractall('.')
base, key = connect()
response = httpx.get(base + '/models', headers={'Authorization': 'Bearer ' + key}, timeout=30)
response.raise_for_status()
assert 'glm-5.3' in [entry['id'] for entry in response.json()['data']]
print('Approved GLM endpoint authenticated; glm-5.3 advertised.', flush=True)
subprocess.run(['git', 'init', 'harbor'], check=True)
subprocess.run(['git', '-C', 'harbor', 'remote', 'add', 'origin', 'https://github.com/marin-community/harbor.git'], check=True)
subprocess.run(['git', '-C', 'harbor', 'fetch', '--depth=1', 'origin', protocol['harbor_commit']], check=True, timeout=300)
subprocess.run(['git', '-C', 'harbor', 'checkout', '--detach', protocol['harbor_commit']], check=True)
env = dict(os.environ)
env.pop('VIRTUAL_ENV', None)
env.pop('PYTHONPATH', None)
env['UV_PROJECT_ENVIRONMENT'] = str(Path('harbor/.venv').resolve())
subprocess.run(['uv', 'sync', '--directory', 'harbor', '--frozen', '--no-dev', '--python', '3.12', '--extra', 'daytona'], env=env, check=True, timeout=1800)
python = str(Path('harbor/.venv/bin/python').resolve())
(output / 'harbor-packages.txt').write_text(subprocess.check_output(['uv', 'pip', 'freeze', '--python', python], env=env, text=True))
judge_token = secrets.token_urlsafe(32)
for name in ['GLM_BULK_TOKEN', 'TOGETHER_API_KEY', 'OPENAI_API_KEY', 'HOSTED_VLLM_API_KEY']:
    env.pop(name, None)
env['JUDGE_PROXY_TOKEN'] = judge_token
with scoped_model_endpoint(base, key, os.environ['TOGETHER_API_KEY'], judge_token, output, protocol) as proxy:
    env['MODEL_PROXY_ROOT'] = proxy
    subprocess.run([python, 'collect.py'], env=env, check=True)
print('Two-task pilot finished; native evidence is in the Iris output archive.', flush=True)
