"""Bounded fixture check: original Dockerfile/egress retained; no implicit rebuild."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).with_name('harbor_docker.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    context = base / 'published' / 'fixture' / 'environment'
    context.mkdir(parents=True)
    (context / 'Dockerfile').write_text('FROM python:3.12-slim\n')
    (base / 'evidence').mkdir()
    original = (context / 'Dockerfile').read_bytes()
    calls = []
    def paths(value):
        value = str(value)
        return base / value.removeprefix('/work/') if value.startswith('/work/') else Path(value)
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1 if command[1:3] == ['image', 'inspect'] else 0)
    def execute(binary, command):
        calls.append((command, {}))
        raise StopIteration
    env = {'BIOTASKS_REAL_DOCKER': '/real/docker', 'BIOTASKS_RUN_ID': 'fixture',
           'CONTEXT_DIR': str(context)}
    globals_ = ['compose', '--project-name', 'fixture', '-f', '/original.yaml']
    with patch.dict(os.environ, env), patch.object(module, 'Path', paths), patch.object(module.subprocess, 'run', run), patch.object(module.subprocess, 'check_output', return_value=b'[{"Id":"sha256:fixture"}]'):
        with patch.object(sys, 'argv', ['docker', *globals_, 'build']):
            assert module.main() == 0
        build = calls[-1]
        assert '--cpu-quota=150000' in build[0] and '--memory=6g' in build[0]
        assert build[1]['env']['DOCKER_BUILDKIT'] == '0'
        with patch.object(module.os, 'execv', execute), patch.object(sys, 'argv', ['docker', *globals_, 'up', '--detach', '--wait']):
            try:
                module.main()
            except StopIteration:
                pass
        command = calls[-1][0]
        assert command[-3:] == ['--no-build', '--pull', 'never']
        assert '/original.yaml' in command
        overlay = json.loads(next((base / 'infra').glob('*.json')).read_text())['services']['main']
        assert overlay['network_mode'] == 'iris-egress' and 'extra_hosts' not in overlay
        assert overlay['mem_limit'] == '6g' and overlay['cpus'] == 1
    assert (context / 'Dockerfile').read_bytes() == original
print('Adapter fixture passed; live Compose merging remains to be checked on TRC.')
