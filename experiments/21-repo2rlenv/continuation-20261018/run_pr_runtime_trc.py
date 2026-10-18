"""No-model TRC controller for the frozen native PR runtime cohort."""
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
    status = {'stage': 'TRC_native_PR_runtime_cohort', 'model_calls': 0, 'status': 'setup'}
    try:
        for filename, expected in [('repo2rlenv-source.tar.gz', '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'), ('pr-inputs.tar.gz', os.environ['BIOTASKS21_PR_INPUTS_SHA256'])]:
            with Path(filename).open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        with tarfile.open('repo2rlenv-source.tar.gz') as archive:
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
            raise TimeoutError('Insufficient remaining native cohort window')
        command = [str(root / '.venv/bin/python'), 'run_pr_runtime_worker.py', '--campaign', 'pr-output', '--worker-name', os.environ['BIOTASKS21_WORKER_NAME'], '--source-archive', 'repo2rlenv-source.tar.gz', '--inputs-archive', 'pr-inputs.tar.gz', '--inputs-sha256', os.environ['BIOTASKS21_PR_INPUTS_SHA256'], '--timeout-sec', str(remaining)]
        status.update(status='cohort_running', child_execution_timeout_seconds=remaining)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        code = capture(command, source=Path('pr-output'), output=output / 'child', timeout=remaining + 240, env=env, maximum_bytes=160 * 1024**2)
        status.update(status='completed' if code == 0 else 'failed', child_exit_code=code)
        return code
    except Exception as exc:
        status.update(status='setup_or_controller_failed', error_type=type(exc).__name__)
        return 1
    finally:
        try:
            summary = {'stage': 'native_PR_runtime_not_independent_admission', 'model_calls': 0, 'native_results_available': False}
            result = Path('pr-output/result.json')
            if result.exists():
                row = json.loads(result.read_text())
                summary['controller'] = {k: row[k] for k in ('status', 'worker_returncode', 'cleanup', 'execution_timeout_sec') if k in row}
            summary['workers'] = [{k: data[k] for k in ('worker_id', 'state', 'started_at', 'ready_at', 'stopped_at') if k in data} for file in Path('pr-output/workers').glob('*.json') for data in [json.loads(file.read_text())]]
            evidence = Path('pr-output/native-evidence.tar.gz')
            if evidence.exists():
                with evidence.open('rb') as stream:
                    summary.update(native_archive_bytes=evidence.stat().st_size, native_archive_sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
                with tarfile.open(evidence, 'r|gz') as archive:
                    for member in archive:
                        if member.name == 'native/cohort/cohort-summary.json':
                            assert member.isfile() and member.size < 1024**2
                            summary.update(native_results_available=True, native_results=json.loads(archive.extractfile(member).read()))
                            break
            (output / 'pr-runtime-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            print('BIOTASKS21_PR_RUNTIME_SUMMARY ' + json.dumps(summary), flush=True)
        except Exception as exc:
            status['summary_error_type'] = type(exc).__name__
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        if Path('pr-output').is_dir() and not (output / 'child/author-evidence.tar.gz').exists():
            preserve(Path('pr-output'), output / 'wrapper-fallback', max_bytes=160 * 1024**2)


if __name__ == '__main__':
    raise SystemExit(main())
