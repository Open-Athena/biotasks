"""No-model TRC controller for the frozen native SWE-gen contrast inputs."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from huggingface_hub import HfApi

from capture_author_process import capture
from preserve_author_output import preserve


def main():
    started = time.monotonic()
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    status = {'stage': 'TRC_saved_native_swe_gen_export', 'model_calls': 0, 'status': 'setup'}
    try:
        for filename, expected in [('repo2rlenv-source.tar.gz', '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'), ('pr-inputs.tar.gz', os.environ['BIOTASKS21_PR_INPUTS_SHA256'])]:
            with Path(filename).open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        manifest = json.loads(Path('manifest.json').read_text())
        remote = manifest['download']
        assert remote['bucket'] == 'open-athena/biotasks' and remote['bytes'] <= 64 * 1024**2
        archive_path = Path('saved-generation-evidence.tar.gz')
        HfApi(token=False).download_bucket_files(remote['bucket'], [(remote['path'], archive_path)], raise_on_missing_files=True, token=False)
        with archive_path.open('rb') as stream:
            assert archive_path.stat().st_size == remote['bytes']
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == remote['sha256']
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
        command = [str(root / '.venv/bin/python'), 'run_swe_gen_saved_export_controller.py', '--campaign', 'swe-gen-export-output', '--worker-name', os.environ['BIOTASKS21_WORKER_NAME'], '--source-archive', 'repo2rlenv-source.tar.gz', '--inputs-archive', 'pr-inputs.tar.gz', '--inputs-sha256', os.environ['BIOTASKS21_PR_INPUTS_SHA256'], '--timeout-sec', str(remaining)]
        status.update(status='cohort_running', child_execution_timeout_seconds=remaining)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        code = capture(command, source=Path('swe-gen-export-output'), output=output / 'child', timeout=remaining + 240, env=env, maximum_bytes=224 * 1024**2)
        status.update(status='completed' if code == 0 else 'failed', child_exit_code=code)
        return code
    except Exception as exc:
        status.update(status='setup_or_controller_failed', error_type=type(exc).__name__)
        return 1
    finally:
        try:
            summary = {'stage': 'native_swe_gen_contrasts_not_author_export_or_admission', 'model_calls': 0, 'native_results_available': False}
            result = Path('swe-gen-export-output/result.json')
            if result.exists():
                row = json.loads(result.read_text())
                summary['controller'] = {k: row[k] for k in ('status', 'worker_returncode', 'cleanup', 'execution_timeout_sec') if k in row}
            summary['workers'] = [{k: data[k] for k in ('worker_id', 'state', 'started_at', 'ready_at', 'stopped_at') if k in data} for file in Path('swe-gen-export-output/workers').glob('*.json') for data in [json.loads(file.read_text())]]
            evidence = Path('swe-gen-export-output/native-evidence.tar.gz')
            if evidence.exists():
                with evidence.open('rb') as stream:
                    summary.update(native_archive_bytes=evidence.stat().st_size, native_archive_sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
                with tarfile.open(evidence, 'r|gz') as archive:
                    for member in archive:
                        if member.name == 'native/swe-gen-export/summary.json':
                            assert member.isfile() and member.size < 1024**2
                            summary.update(native_results_available=True, native_results=json.loads(archive.extractfile(member).read()))
                            break
            (output / 'swe-gen-export-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            print('BIOTASKS21_SWE_GEN_CONTRAST_SUMMARY ' + json.dumps(summary), flush=True)
        except Exception as exc:
            status['summary_error_type'] = type(exc).__name__
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        if Path('swe-gen-export-output').is_dir() and not (output / 'child/author-evidence.tar.gz').exists():
            preserve(Path('swe-gen-export-output'), output / 'wrapper-fallback', max_bytes=224 * 1024**2)


if __name__ == '__main__':
    raise SystemExit(main())
