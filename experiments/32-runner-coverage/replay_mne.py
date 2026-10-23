"""Frozen transcript replay using pinned upstream clone, sandbox and checks.

No generation or repair. The Docker call adapter adds resource/ownership limits,
records results and prevents further work after a timeout. Shared base cache is
not owned. Only an explicitly retained completed image can outlive this job.
"""
import ast
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
from types import SimpleNamespace
import urllib.request
from collections.abc import Callable

from recorded_replay import replay_recorded_actions

ROOT = Path(__file__).resolve().parent
OWNER = 'biotasks32-mne-recorded-001'
LABEL = 'org.open-athena.biotasks.owner=' + OWNER
TAG = OWNER + ':recorded-actions'
TOOLS = ROOT / 'replay-tools'
CONTEXT = ROOT / 'replay-context'
OUT = Path(os.environ.get('IRIS_OUTPUT_DIR', str(ROOT / 'unused-output')))
REPORT = {'run_id': OWNER, 'model_calls': 0, 'controls_run': 0,
          'commands_edited': False, 'new_capacity': False}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_functions(path, names, namespace):
    """Compile selected original AST nodes with no source rewrite."""
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)


def load_post_checks(path, namespace):
    """Exact original smoke/git statements; no model or other bootstrap stages."""
    tree = ast.parse(path.read_text())
    nodes = sorted([n for n in ast.walk(tree) if isinstance(n, ast.stmt) and n.lineno in (630, 631, 650, 651)], key=lambda n: n.lineno)
    assert len(nodes) == 4
    assert [n.end_lineno for n in nodes] == [630, 640, 650, 665]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def docker(*args, timeout=30, check=True):
    return subprocess.run([str(TOOLS / 'docker'), *args], capture_output=True, text=True, timeout=timeout, check=check)


def setup_tool():
    pins = json.loads((ROOT / 'docker-tool.json').read_text())
    TOOLS.mkdir()
    archive = TOOLS / 'docker.tgz'
    with urllib.request.urlopen(pins['docker_url'], timeout=60) as src, archive.open('wb') as dst:
        size = 0
        while chunk := src.read(1024 * 1024):
            size += len(chunk)
            assert size < 100 * 1024**2
            dst.write(chunk)
    assert digest(archive.read_bytes()) == pins['docker_sha256']
    with tarfile.open(archive) as tf:
        (TOOLS / 'docker').write_bytes(tf.extractfile('docker/docker').read())
    (TOOLS / 'docker').chmod(0o755)
    archive.unlink()
    os.environ['PATH'] = str(TOOLS) + ':' + os.environ['PATH']
    assert not docker('ps', '-aq', '--filter', 'label=' + LABEL).stdout.strip()
    assert docker('image', 'inspect', TAG, check=False).returncode != 0
    info = json.loads(docker('info', '--format', '{{json .}}').stdout)
    assert info['MemoryLimit'] and info['CpuCfsQuota']


def cleanup():
    """Independent of replay deadline/adapter and idempotent after partial start."""
    errors = []
    if (TOOLS / 'docker').exists():
        try:
            ids = docker('ps', '-aq', '--filter', 'label=' + LABEL).stdout.split()
            if ids:
                docker('rm', '-f', *ids, timeout=120)
            REPORT['owned_containers_absent'] = not docker('ps', '-aq', '--filter', 'label=' + LABEL).stdout.strip()
            keep = REPORT.get('retained_image_id')
            for _ in range(16):
                remaining = set(docker('image', 'ls', '-aq', '--filter', 'label=' + LABEL).stdout.split())
                removed = False
                for image_id in remaining:
                    inspected = docker('image', 'inspect', image_id, check=False)
                    if inspected.returncode:
                        continue
                    details = json.loads(inspected.stdout)[0]
                    assert details['Config']['Labels']['org.open-athena.biotasks.owner'] == OWNER
                    if details['Id'] != keep:
                        removed |= docker('image', 'rm', '-f', image_id, timeout=30, check=False).returncode == 0
                if not removed:
                    break
            REPORT['owned_image_ids_remaining'] = docker('image', 'ls', '-aq', '--filter', 'label=' + LABEL).stdout.split()
            REPORT['cleanup_verified'] = REPORT['owned_containers_absent'] and (
                (not REPORT['owned_image_ids_remaining'] and keep is None) or
                (keep is not None and len(REPORT['owned_image_ids_remaining']) == 1))
        except Exception as error:
            errors.append(type(error).__name__ + ': ' + str(error)[:300])
    for path in (CONTEXT, TOOLS):
        try:
            if path.exists():
                shutil.rmtree(path)
        except Exception as error:
            errors.append(type(error).__name__ + ': ' + str(error)[:300])
    REPORT['context_tools_removed'] = not CONTEXT.exists() and not TOOLS.exists()
    REPORT['cleanup_errors'] = errors


def main():
    assert os.environ['BIOTASKS_RUN_ID'] == OWNER
    assert not any(os.environ.get(k) for k in ('OPENROUTER_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN', 'CW_KEY_SECRET'))
    REPORT['started'] = time.time()
    deadline = time.monotonic() + 3900
    def interrupted(sig, frame):
        raise RuntimeError('received signal ' + str(sig))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        payload_bytes = (ROOT / 'replay.json').read_bytes()
        assert digest(payload_bytes) == '99cf1811aa3d2165f925072492f8a360ffff7b8d6460972279fe26f80e739f4f'
        payload = json.loads(payload_bytes)
        REPORT['payload_sha256'] = digest(payload_bytes)
        assert payload['repo'] == 'mne-tools/mne-python'
        assert payload['ref'] == '349e64dc5b446e489352d07d61df807b5f78ec9c'
        pins = json.loads((ROOT / 'source-pins.json').read_text())
        for name, sha in pins.items():
            assert digest((ROOT / name).read_bytes()) == sha
        REPORT['source_sha256'] = pins
        setup_tool()
        spec = importlib.util.spec_from_file_location('original_docker', ROOT / 'docker_original.py')
        original = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = original
        spec.loader.exec_module(original)
        native_run = original._run
        sequence = 0
        def bounded_run(args, *, timeout=600, input_text=None):
            nonlocal sequence
            if REPORT.get('client_timeout'):
                raise RuntimeError('No further work after client timeout; cleanup only')
            if time.monotonic() + timeout > deadline:
                raise RuntimeError('Full command timeout does not fit work deadline')
            call = list(args)
            assert call[0] == 'docker'
            if call[1] == 'run':
                call[2:2] = ['--cpus', '1.5', '--memory', '6g', '--memory-swap', '6g', '--network', 'iris-egress', '--label', LABEL]
            result = native_run(call, timeout=timeout, input_text=input_text)
            sequence += 1
            row = {'sequence': sequence, 'command_sha256': digest(json.dumps(args).encode()),
                   'docker_operation': args[1], 'exit_code': result.exit_code,
                   'timeout_seconds': timeout, 'duration_sec': result.duration_sec}
            for stream in ('stdout', 'stderr'):
                data = getattr(result, stream).encode()
                (OUT / f'call-{sequence:03d}-{stream}.txt').write_bytes(data)
                row[stream + '_sha256'] = digest(data)
            with (OUT / 'docker-calls.jsonl').open('a') as f:
                f.write(json.dumps(row) + '\n')
            if result.exit_code == 124:
                REPORT['client_timeout'] = True
            return result
        original._run = bounded_run
        namespace = dict(globals(), logger=logging.getLogger('pinned-replay'), _run=bounded_run)
        load_functions(ROOT / 'auth_original.py', {'auth_clone_url'}, namespace)
        load_functions(ROOT / 'runner_original.py', {'BootstrapError', '_scrub_token', '_run_git_streaming', '_shallow_clone_at_ref', '_resolve_head_sha', '_verify_committed_image'}, namespace)
        namespace['_shallow_clone_at_ref']('https://github.com/' + payload['repo'] + '.git', payload['ref'], None, CONTEXT)
        assert namespace['_resolve_head_sha'](CONTEXT) == payload['ref']
        REPORT['source_commit'] = payload['ref']
        sandbox = original.DockerSandbox.start(payload['base_image'], CONTEXT, platform='linux/amd64')
        config = json.loads(docker('inspect', sandbox.container_id).stdout)[0]
        assert config['HostConfig']['NanoCpus'] == 1500000000
        assert config['HostConfig']['Memory'] == 6 * 1024**3
        assert config['HostConfig']['NetworkMode'] == 'iris-egress'
        REPORT['base_image_id'] = config['Image']
        REPORT['full_checkout_copy'] = True
        REPORT['replay'] = replay_recorded_actions(sandbox, payload['actions'], OUT / 'actions')
        if REPORT['replay']['status'] != 'matched_recorded_exits':
            return
        namespace.update(sandbox=sandbox, outcome=SimpleNamespace(test_cmds=payload['test_cmds']), _emit=lambda *a, **kw: None)
        load_post_checks(ROOT / 'runner_original.py', namespace)
        REPORT['smoke_passed'] = namespace['smoke_ok']
        REPORT['image_id'] = sandbox.commit(TAG)
        REPORT['verify_passed'], REPORT['verify_detail'] = namespace['_verify_committed_image'](TAG, payload['test_cmds'], platform='linux/amd64')
        if REPORT.get('client_timeout'):
            return
        inspected = json.loads(docker('image', 'inspect', TAG).stdout)[0]
        assert inspected['Id'] == REPORT['image_id']
        assert inspected['Config']['Labels']['org.open-athena.biotasks.owner'] == OWNER
        REPORT['retained_image_id'] = inspected['Id']
        REPORT['retained_image_tag'] = TAG
        REPORT['retention_condition'] = 'Pending frozen MNE PR14445 comparison on this worker; delete after controls or investigation termination. Not original image bytes.'
    except Exception as error:
        REPORT['error_type'] = type(error).__name__
        REPORT['error'] = str(error)[:500]
    finally:
        try:
            cleanup()
        finally:
            REPORT['finished'] = time.time()
            (OUT / 'mne-recorded-result.json').write_text(json.dumps(REPORT, indent=2) + '\n')
            print('BIOTASKS32_RESULT=' + json.dumps(REPORT), flush=True)
    assert REPORT.get('cleanup_verified') and not REPORT.get('error'), 'Inspect preserved evidence; no repair/retry'


if __name__ == '__main__':
    main()
