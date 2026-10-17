"""Run only the pinned native history source filter; no models or test execution."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path


def main():
    started = time.monotonic()
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    status = {'stage': 'native_history_source_intake', 'model_calls': 0,
              'test_executions': 0, 'candidate_generation_attempts': 0}
    try:
        source = Path('repo2rlenv-source.tar.gz')
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        config = json.loads(Path('intake-config.json').read_text())
        assert config.get('mode') != 'evaluate'
        assert config['recipe'] == 'r2e_gym'
        assert config['repo']['ref'] == 'c911b1210e69df202834418ec43fba62a9d0b100'
        assert config['repo']['url'] == 'https://github.com/biopython/biopython'
        assert config['options']['source_paths'] == ['Bio']
        assert config['options']['test_paths'] == ['Tests']
        assert config['options']['history_limit'] == 2000
        assert config['options']['max_candidates'] == 10
        with tarfile.open(source) as archive:
            archive.extractall('runtime', filter='data')
        roots = list(Path('runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve()/'.venv')
        with (output/'setup.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--python', '3.12.3', '--project', str(root)],
                           env=env, stdout=log, stderr=log, check=True, timeout=600)
        # The pinned module's prepare branch only clones and inspects history.
        # Its evaluate branch (builds and tests) is never selected.
        assert config.get('mode') != 'evaluate'
        env['REPO2RLENV_REMOTE_WORKER'] = '1'
        remaining = int(1500 - (time.monotonic() - started))
        if remaining < 300:
            raise TimeoutError('Insufficient intake window')
        with (output/'intake.log').open('w') as log:
            subprocess.run([str(root/'.venv/bin/python'), '-m', 'repo2rlenv.pipelines.recipes.history.worker',
                            'intake-config.json', str(output/'selection')], env=env,
                           stdout=log, stderr=log, check=True, timeout=remaining)
        selected = json.loads((output/'selection/generation.json').read_text())
        status.update(status='completed', eligible_sources=len(selected['candidates']),
                      history_records_considered=selected['attempted'],
                      limitations=['Source intake only; no build, contrast, authoring or acceptance',
                                   'Broader fixture/bootstrap profile requires review before generation'])
        return 0
    except Exception as exc:
        status.update(status='failed', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output/'status.json').write_text(json.dumps(status, indent=2)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
