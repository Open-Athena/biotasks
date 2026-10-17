"""Fresh history runtime controls with no model calls and a 30-minute deadline."""
import json
import os
import subprocess
import tarfile
import time
import hashlib
from pathlib import Path
from package_provider_task import unpack
from history_runtime_input import check_task


def main():
    started = time.monotonic()
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    try:
        unpack(Path('task-bundle.tar.gz'), Path('task-bundle-manifest.json'),
               Path('.'), maximum_bytes=384*1024**2)
        check_task(Path('task'), Path('input-review.json'))
        source = Path('repo2rlenv-source.tar.gz')
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest() == '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(source) as archive:
            archive.extractall('source', filter='data')
        roots = list(Path('source').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV',None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve()/'.venv')
        with (output/'dependency-setup.log').open('w') as log:
            subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor',
                            '--extra','daytona','--python','3.12.3','--project',str(root)],
                           env=env,stdout=log,stderr=log,check=True,timeout=600)
        remaining = int(1800-(time.monotonic()-started))
        if remaining < 60:
            raise TimeoutError('Compatibility setup exhausted deadline')
        env.update(REPO2RLENV_MODEL_WORKER='1', BIOTASKS21_PREFLIGHT_REMAINING_SEC=str(remaining))
        with (output/'provider-controller.log').open('w') as log:
            result = subprocess.run([str(root/'.venv/bin/python'), 'run_history_provider_preflight.py',
                                     '--task','task','--input-review','input-review.json',
                                     '--output','provider-output'],env=env,stdout=log,stderr=log,
                                    timeout=remaining+240)
        (output/'wrapper-status.json').write_text(json.dumps({'stage':'history_runtime_probe','child_exit_code':result.returncode,'model_calls':0}))
        return result.returncode
    except Exception as exc:
        (output/'wrapper-status.json').write_text(json.dumps({'stage':'setup_or_controller','error_type':type(exc).__name__,'model_calls':0}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
