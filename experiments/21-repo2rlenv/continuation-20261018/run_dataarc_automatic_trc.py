"""Run the pinned native DataArc pipeline unchanged behind a fixed transport.

The wrapper handles input unpacking, dependency setup, zero-model transport
preflight, deadline/capture and the existing native controller. It never edits
or repairs generated task artifacts and supplies no task-specific feedback.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request

from package_provider_task import unpack
from preserve_author_output import preserve


def main():
    started = time.monotonic()
    capture = Path(os.environ['IRIS_OUTPUT_DIR'])
    capture.mkdir(parents=True, exist_ok=True)
    status = {'stage': 'fixed_automatic_dataarc_wrapper',
              'external_task_feedback': False, 'manual_output_fixes': 0}
    try:
        unpack(Path('parent-bundle.tar.gz'), Path('parent-bundle-manifest.json'), Path('.'))
        Path('task').rename('parent')
        source = Path('repo2rlenv-source.tar.gz')
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        base = os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/')
        application = os.environ['BIOTASKS21_GENERATION_CLIENT_TOKEN']
        body = json.dumps({'model': 'glm-5.3', 'max_tokens': 131072,
                           'chat_template_kwargs': {'reasoning_effort': 'medium'},
                           'messages': [{'role': 'user', 'content': 'Transport receipt only.'}]}).encode()
        request = urllib.request.Request(base + '/v1/transport-check', data=body,
            headers={'Content-Type': 'application/json',
                     'X-Biotasks21-Inference-Token': application})
        with urllib.request.urlopen(request, timeout=30) as response:
            receipt = json.load(response)
        assert receipt['model_calls'] == 0 and receipt['request_sha256'] == hashlib.sha256(body).hexdigest()
        (capture / 'transport-preflight.json').write_text(json.dumps(receipt, indent=2) + '\n')
        with tarfile.open(source) as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP='True')
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        with (capture / 'private-setup.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor',
                            '--extra', 'daytona', '--python', '3.12.3', '--project', str(root)],
                           env=env, stdout=log, stderr=log, check=True, timeout=600)
            subprocess.run(['uv', 'build', '--wheel', '--project', str(root)], env=env,
                           stdout=log, stderr=log, check=True, timeout=300)
        wheels = list((root / 'dist').glob('*.whl'))
        assert len(wheels) == 1
        remaining = int(os.environ['BIOTASKS21_TOTAL_DEADLINE_SEC']) - int(time.monotonic() - started)
        if not 900 <= remaining <= 6900:
            raise TimeoutError('Insufficient fixed automatic generation window')
        env.update(REPO2RLENV_MODEL_WORKER='1', BIOTASKS21_GLM_ENDPOINT=base + '/v1',
                   BIOTASKS21_GLM_KEY=application, BIOTASKS21_CONTROLLER_DEADLINE=str(remaining))
        with (capture / 'private-controller.log').open('w') as log:
            result = subprocess.run([str(root / '.venv/bin/python'), 'run_dataarc_build.py',
                '--campaign', 'author-output', '--wheel', str(wheels[0]), '--parent', 'parent',
                '--manifest', 'parent-manifest.json', '--adaptation', 'glm-generation-adaptation.json',
                '--worker-name', os.environ['BIOTASKS21_WORKER_NAME']], env=env,
                stdout=log, stderr=log, timeout=remaining + 240)
        status.update(child_exit_code=result.returncode,
                      status='completed' if result.returncode == 0 else 'native_pipeline_failed')
        return result.returncode
    except Exception as exc:
        status.update(status='setup_or_native_pipeline_failed', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (capture / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        if Path('author-output').is_dir() and not (capture / 'after-cleanup/author-evidence.tar.gz').exists():
            preserve(Path('author-output'), capture / 'wrapper-fallback')


if __name__ == '__main__':
    raise SystemExit(main())
