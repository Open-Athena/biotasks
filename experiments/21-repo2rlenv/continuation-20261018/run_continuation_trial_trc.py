"""Pinned TRC setup and bounded capture for one admitted task/provider cohort."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    state = {'stage': 'native_provider_and_single_blind_setup', 'status': 'started'}
    try:
        for name, expected in [('repo2rlenv-source.tar.gz', '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'),
                               ('task-bundle.tar.gz', os.environ['BIOTASKS21_TASK_ARCHIVE_SHA256'])]:
            with Path(name).open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        with tarfile.open('repo2rlenv-source.tar.gz') as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        with tarfile.open('task-bundle.tar.gz') as archive:
            archive.extractall('.', filter='data')
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP='True')
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        with (output / 'private-controller.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor', '--extra', 'daytona',
                            '--python', '3.12.3', '--project', str(root)], env=env,
                           stdout=log, stderr=log, check=True, timeout=600)
            env['REPO2RLENV_MODEL_WORKER'] = '1'
            result = subprocess.run([str(root / '.venv/bin/python'), 'run_continuation_blind_trial.py'],
                                    env=env, stdout=log, stderr=log, timeout=6000)
        state.update(status='completed' if result.returncode == 0 else 'failed',
                     child_exit_code=result.returncode)
        return result.returncode
    except Exception as exc:
        state.update(status='setup_or_controller_failure', error_type=type(exc).__name__)
        return 1
    finally:
        state['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(state, indent=2) + '\n')
        # These originals include private SDK routes/config and require separate
        # credential/route eligibility review before any public publication.
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
