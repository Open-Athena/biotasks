"""Check remote wrapper wiring without models, workers, or package installation."""
import json
import os
import runpy
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('run_endless_remote.py').resolve()
DIGEST = '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'


def check(child_code=0, setup_fails=False):
    calls = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        output = root / 'output'
        (root / 'repo2rlenv-source.tar.gz').write_bytes(b'fixture')
        package = root / 'r2e' / 'package'
        (package / 'dist').mkdir(parents=True)
        (package / 'dist' / 'fixture.whl').write_bytes(b'wheel')
        relay = types.SimpleNamespace(resolve=lambda _: types.SimpleNamespace(
            endpoints=[types.SimpleNamespace(url='https://example.invalid')]))
        client = types.ModuleType('iris.client.client')
        client.iris_ctx = lambda: types.SimpleNamespace(client=types.SimpleNamespace(
            resolver_for_job=lambda _: relay))
        cluster = types.ModuleType('iris.cluster.types')
        cluster.JobName = types.SimpleNamespace(from_string=lambda x: x)
        def fake_capture(command, **kwargs):
            calls.append((command, kwargs))
            assert command[1] == 'run_endless_controller.py'
            assert command[-1] == 'biotasks21-endless-biological-01'
            assert kwargs['output'] == output / 'child'
            assert kwargs['source'] == Path('author-output')
            assert 900 <= int(kwargs['env']['BIOTASKS21_CONTROLLER_DEADLINE']) <= 6900
            assert kwargs['timeout'] <= 7140
            assert kwargs['env']['BIOTASKS21_GLM_ENDPOINT'] == 'https://example.invalid/v1'
            return child_code
        before = Path.cwd()
        try:
            os.chdir(root)
            with patch.dict(sys.modules, {'iris.client.client': client, 'iris.cluster.types': cluster}), patch.dict(os.environ, {'IRIS_OUTPUT_DIR': str(output)}), patch('hashlib.sha256') as sha, patch('tarfile.open'), patch('subprocess.run') as run, patch('capture_author_process.capture', fake_capture):
                sha.return_value.hexdigest.return_value = DIGEST
                if setup_fails:
                    run.side_effect = RuntimeError('setup fixture failure')
                try:
                    runpy.run_path(str(SCRIPT), run_name='__main__')
                except SystemExit as exc:
                    assert exc.code == (1 if setup_fails else child_code)
                else:
                    raise AssertionError('Wrapper did not return an exit status')
            status = json.loads((output / 'wrapper-status.json').read_text())
            if setup_fails:
                assert status['error_type'] == 'RuntimeError' and not calls
            else:
                assert status['child_exit_code'] == child_code and len(calls) == 1
        finally:
            os.chdir(before)


if __name__ == '__main__':
    check()
    check(child_code=124)
    check(setup_fails=True)
    print(json.dumps({'stage': 'mocked_remote_wrapper', 'cases': ['success', 'child_timeout', 'setup_failure'], 'passed': True, 'model_calls': 0, 'remote_workers': 0}))
