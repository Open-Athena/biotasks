"""Frozen Matchms comparison through complete, unchanged upstream validate_pr.

This driver selects a transport, owns one bounded container per arm, records
calls, and aborts an arm after a client timeout. It does not repair task inputs.
Raw outputs are private. --check performs imports/hash/stage checks only.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parent
LABEL_KEY = 'org.open-athena.biotasks.owner'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path, package=False):
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[str(path.parent)] if package else None)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def load_sources():
    # Namespace shells replace package startup only. All imported validator,
    # dispatch, parser and executor files are hash-bound upstream sources.
    for name, path in [('repo2rlenv', ROOT/'upstream'),
                       ('repo2rlenv.bootstrap', ROOT/'upstream/bootstrap'),
                       ('repo2rlenv.pipelines', ROOT/'upstream/pipelines')]:
        value = types.ModuleType(name)
        value.__path__ = [str(path)]
        sys.modules[name] = value
    original = module('repo2rlenv.bootstrap.docker', ROOT/'upstream/bootstrap/docker.py')
    candidate = module('transport_candidate', ROOT/'candidate/docker.py')
    parsers = module('repo2rlenv.log_parsers', ROOT/'upstream/log_parsers/__init__.py', True)
    validator = module('repo2rlenv.pipelines.pr_runtime_validate', ROOT/'upstream/pipelines/pr_runtime_validate.py')
    return original, candidate, parsers, validator


def verify_inputs(validator):
    provenance = json.loads((ROOT/'provenance.json').read_text())
    for row in provenance['files']:
        assert digest((ROOT/row['path']).read_bytes()) == row['sha256'], row['path']
    assert digest((ROOT/'candidate/docker.py').read_bytes()) == 'fed64fdffe68249fc1c24f89849181f8da3890b778ee8b6e783a6cd533a9c522'
    manifest = json.loads((ROOT/'live-script-manifest.json').read_text())
    assert [row['pr'] for row in manifest['cases']] == [958, 671]
    for case in manifest['cases']:
        patches = {}
        for kind in ('source', 'test'):
            data = (ROOT/'inputs-private'/f"{case['pr']}-{kind}.patch").read_bytes()
            assert digest(data) == case[kind+'_patch_sha256']
            patches[kind] = data.decode()
        for side in ('pre', 'post'):
            script = validator._build_stage_script(case['base_sha'],
                apply_patch=patches['source'] if side == 'post' else None,
                apply_test_patch=patches['test'], test_cmds=case['commands'])
            data = script.encode()
            assert digest(data) == case['stages'][side]['sha256']
            assert data == (ROOT/'inputs-private'/f"{case['pr']}-{side}.sh").read_bytes()
    return manifest


class ArmTimeout(RuntimeError):
    pass


class RecordedSandbox:
    def __init__(self, sandbox, output, case):
        self.sandbox, self.output, self.case = sandbox, output, case
        self.calls = []

    def exec(self, command, *, timeout=300):
        checksum = digest(command.encode())
        stage = next((name for name, info in self.case['stages'].items()
                      if info['sha256'] == checksum), None)
        if 'echo R2E_START_TEST_OUTPUT' in command:
            assert stage is not None, 'Unexpected validation script: frozen inputs changed'
        row = {'index': len(self.calls), 'command_sha256': checksum,
               'command_bytes': len(command.encode()), 'stage': stage,
               'timeout': timeout, 'started': time.time()}
        self.calls.append(row)
        try:
            result = self.sandbox.exec(command, timeout=timeout)
            row.update(exit_code=result.exit_code, duration_sec=result.duration_sec)
            for stream in ('stdout', 'stderr'):
                data = getattr(result, stream).encode()
                path = self.output/f"call-{row['index']:02d}-{stream}.txt"
                path.write_bytes(data)
                path.chmod(0o600)
                row[stream+'_sha256'] = digest(data)
                row[stream+'_bytes'] = len(data)
            if result.exit_code == 124:
                # Same guard in both arms. Never allow a still-running remote
                # command to overlap the next stage. Owner removes container.
                raise ArmTimeout('Client timeout: arm censored, sandbox removal required')
            return result
        except OSError as error:
            row.update(exception=type(error).__name__, errno=error.errno)
            raise
        finally:
            row['finished'] = time.time()
            (self.output/'calls.json').write_text(json.dumps(self.calls, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--image')
    parser.add_argument('--owner')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    original, candidate, parsers, validator = load_sources()
    manifest = verify_inputs(validator)
    if args.check:
        assert parsers.parse_logs(['python -m pytest -v'], 'tests/test_a.py::test_a PASSED [100%]\n') == {'tests/test_a.py::test_a': 'PASSED'}
        print(json.dumps({'source_imports': 'passed', 'frozen_stages': 4,
                          'parser_dispatch': 'passed', 'docker_execution': False}))
        return
    assert os.environ.get('BIOTASKS30_BOUNDED_SUPERVISOR') == '1'
    assert args.owner and args.owner.startswith('biotasks30-')
    assert args.image and args.image.startswith('sha256:')
    assert args.output and not args.output.exists()
    args.output.mkdir(parents=True, mode=0o700)
    label = LABEL_KEY+'='+args.owner

    def docker(*items, check=True):
        return subprocess.run(['docker', *items], capture_output=True, text=True,
                              timeout=45, check=check)

    image = json.loads(docker('image', 'inspect', args.image).stdout)[0]
    assert image['Id'] == args.image
    assert image['Config']['Labels'][LABEL_KEY] == args.owner
    assert not docker('ps', '-aq', '--filter', 'label='+label).stdout.strip()
    results = {'image_id': args.image, 'owner': args.owner, 'model_calls': 0,
               'timeout_guard': 'Abort arm and remove sandbox on any exec exit 124',
               'arms': [], 'started': time.time()}
    try:
        for case in manifest['cases']:
            for name, executor in [('original', original), ('stdin', candidate)]:
                out = args.output/f"{case['pr']}-{name}"
                out.mkdir(mode=0o700)
                arm = {'pr': case['pr'], 'transport': name, 'started': time.time()}
                results['arms'].append(arm)
                cid = None
                recorder = None
                try:
                    # A fresh clone of the same built image per arm prevents
                    # previous patches/fetches from influencing later arms.
                    cid = docker('run', '-d', '--label', label, '--cpus=1',
                        '--memory=6g', '--memory-swap=6g', '--pids-limit=512',
                        '--network=iris-egress', '--entrypoint=/bin/bash', args.image,
                        '-c', 'sleep 8200').stdout.strip()
                    assert cid and all(c in '0123456789abcdef' for c in cid)
                    sandbox = executor.DockerSandbox(cid, '/workspace', 'linux/amd64')
                    recorder = RecordedSandbox(sandbox, out, case)
                    outcome = validator.validate_pr(sandbox=recorder,
                        base_commit=case['base_sha'],
                        patch=(ROOT/'inputs-private'/f"{case['pr']}-source.patch").read_text(),
                        test_patch=(ROOT/'inputs-private'/f"{case['pr']}-test.patch").read_text(),
                        test_cmds=case['commands'], language='python', timeout=600)
                    record = dataclasses.asdict(outcome)
                    (out/'outcome-private.json').write_text(json.dumps(record, indent=2)+'\n')
                    arm.update(status=outcome.status, reason=outcome.reason,
                               f2p_count=len(outcome.fail_to_pass), p2p_count=len(outcome.pass_to_pass))
                except (OSError, ArmTimeout) as error:
                    arm.update(status='exception' if isinstance(error, OSError) else 'censored_timeout',
                               exception=type(error).__name__, errno=getattr(error, 'errno', None))
                finally:
                    if cid:
                        detail = json.loads(docker('inspect', cid).stdout)[0]
                        assert detail['Config']['Labels'][LABEL_KEY] == args.owner
                        docker('rm', '-f', cid)
                        assert docker('inspect', cid, check=False).returncode != 0
                        arm['container_removed'] = True
                    arm['calls'] = recorder.calls if recorder else []
                    arm['finished'] = time.time()
                    (args.output/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    finally:
        remaining = docker('ps', '-aq', '--filter', 'label='+label).stdout.split()
        if remaining:
            docker('rm', '-f', *remaining)
        results['owned_containers_absent'] = not docker('ps', '-aq', '--filter', 'label='+label).stdout.strip()
        results['finished'] = time.time()
        (args.output/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    assert results['owned_containers_absent']


if __name__ == '__main__':
    main()
