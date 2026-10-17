"""Iris wrapper for no-model native history controls with supported output capture."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path
from capture_author_process import capture


def main():
    started=time.monotonic()
    output=Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True,exist_ok=True)
    try:
        archive=Path('repo2rlenv-source.tar.gz')
        with archive.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()=='7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(archive) as tar:tar.extractall('runtime',filter='data')
        roots=list(Path('runtime').iterdir());assert len(roots)==1
        root=roots[0]
        env=dict(os.environ);env.pop('VIRTUAL_ENV',None)
        env['UV_PROJECT_ENVIRONMENT']=str(root.resolve()/'.venv')
        with (output/'dependency-setup.log').open('w') as log:
            subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor','--extra','daytona','--python','3.12.3','--project',str(root)],env=env,stdout=log,stderr=log,check=True,timeout=600)
        remaining=int(6900-(time.monotonic()-started))
        if remaining<900:raise TimeoutError('Insufficient control execution window')
        env['BIOTASKS21_CONTROLLER_DEADLINE']=str(remaining)
        command=[str(root/'.venv/bin/python'),'run_smith_controls.py','--stage','history-independent',
                 '--campaign','control-output','--worker-name',os.environ['BIOTASKS21_WORKER_NAME'],
                 '--source-archive','repo2rlenv-source.tar.gz','--generation-archive','task-evidence.tar.gz','--config','control-config.json']
        return capture(command,source=Path('control-output'),output=output,timeout=remaining+240,env=env)
    except Exception as exc:
        (output/'wrapper-failure.json').write_text(json.dumps({'error_type':type(exc).__name__,'stage':'setup_or_controller'}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
