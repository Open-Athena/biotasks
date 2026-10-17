"""Remote setup-only diagnostic: no provider clients, credentials, or model calls."""
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
import traceback
from pathlib import Path


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    state = {'stage': 'setup_only', 'phase': 'input_check', 'model_calls': 0,
             'provider_api_calls': 0, 'provider_allocations': 0}
    started = time.monotonic()
    try:
        required = ['repo2rlenv-source.tar.gz', 'task-file-modes.json', 'acceptance.json',
                    'task-bundle.tar.gz', 'task-bundle-manifest.json', 'package_provider_task.py',
                    'run_pr_provider_preflight.py', 'pr_provider_environment.py',
                    'preserve_author_output.py']
        state['input_presence'] = {name: Path(name).is_file() for name in required}
        if not all(state['input_presence'].values()):
            raise FileNotFoundError('Missing setup input; see input_presence')
        state['phase'] = 'task_archive_unpack'
        from package_provider_task import unpack
        transfer_limit = int(os.environ.get('BIOTASKS21_TASK_TRANSFER_MAX_BYTES', 4 * 1024**2))
        state['task_transfer_max_bytes'] = transfer_limit
        unpack(Path('task-bundle.tar.gz'), Path('task-bundle-manifest.json'), Path('.'),
               maximum_bytes=transfer_limit)
        modes = json.loads(Path('task-file-modes.json').read_text())
        missing = [name for name in modes if not (Path('task') / name).is_file()]
        state['missing_task_paths'] = missing
        if missing:
            raise FileNotFoundError('Missing transferred task assets')
        source = Path('repo2rlenv-source.tar.gz')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        state['phase'] = 'source_extraction'
        with tarfile.open(source) as archive:
            archive.extractall('source', filter='data')
        roots = list(Path('source').iterdir())
        assert len(roots) == 1
        root = roots[0]
        state['uv_executable'] = shutil.which('uv')
        state['phase'] = 'dependency_setup'
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        with (output / 'dependency-setup.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor',
                            '--extra', 'daytona', '--python', '3.12.3', '--project', str(root)],
                           env=env, stdout=log, stderr=log, check=True, timeout=600)
        state['phase'] = 'file_modes'
        for name, mode in modes.items():
            rel = Path(name)
            assert not rel.is_absolute() and '..' not in rel.parts
            (Path('task') / rel).chmod(mode)
        python = root / '.venv/bin/python'
        state['python_executable_exists'] = python.is_file()
        state['phase'] = 'controller_import_and_task_check'
        code = "from pathlib import Path; from run_pr_provider_preflight import check_task,config; check_task(Path('task'),Path('acceptance.json')); config(Path('task'),Path('unused-output'),'nop'); print('controller import, accepted asset hashes, and native config passed')"
        with (output / 'controller-check.log').open('w') as log:
            subprocess.run([str(python), '-c', code], env=env, stdout=log, stderr=log,
                           check=True, timeout=120)
        state.update(status='passed', phase='complete')
        return root, env
    except Exception as exc:
        state.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        (output / 'traceback.txt').write_text(traceback.format_exc())
        raise
    finally:
        state['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'setup-diagnostic.json').write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    main()
