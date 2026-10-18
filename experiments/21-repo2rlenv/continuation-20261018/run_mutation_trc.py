"""Run a no-model mutation contrast controller on pinned existing TRC CPU capacity."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from capture_author_process import capture
from preserve_author_output import preserve


def main():
    started = time.monotonic()
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    status = {'stage': 'trc_mutation_contrast', 'model_calls': 0, 'status': 'setup'}
    try:
        source = Path('repo2rlenv-source.tar.gz')
        assert hashlib.sha256(source.read_bytes()).hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(source) as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor', '--extra', 'daytona', '--python', '3.12.3', '--project', str(root)], env=env, check=True, timeout=600)
        remaining = int(6900 - (time.monotonic() - started))
        if remaining < 900:
            raise TimeoutError('Insufficient remaining contrast window')
        command = [str(root / '.venv/bin/python'), 'run_swe_smith_worker.py', '--campaign', 'contrast-output', '--worker-name', os.environ['BIOTASKS21_WORKER_NAME'], '--source-archive', str(source), '--config', 'profile.json', '--timeout-sec', str(remaining)]
        status.update(status='contrast_running', child_execution_timeout_seconds=remaining)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        code = capture(command, source=Path('contrast-output'), output=output / 'child', timeout=remaining + 240, env=env, maximum_bytes=256 * 1024**2)
        status.update(status='completed' if code == 0 else 'failed', child_exit_code=code)
        return code
    except Exception as exc:
        status.update(status='setup_or_controller_failed', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        if Path('contrast-output').is_dir() and not (output / 'child/author-evidence.tar.gz').exists():
            preserve(Path('contrast-output'), output / 'wrapper-fallback', max_bytes=256 * 1024**2)


if __name__ == '__main__':
    raise SystemExit(main())
