"""Iris wrapper for the no-model scikit-bio native commit-runtime profile."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path
from capture_author_process import capture


INPUT_SHA256 = {
    'commit-71912.json': '38c7f4a7495a55b09f6ea1dd7367b162302ab1879ce860ef2bd99808b8ac1241',
    'commit-71912.diff': '39752db1ddb4328dc6004cfc6599b3d07426dad061bcb4671757a338d9808a51',
}


def prepare_commit_inputs(directory):
    """Reconstruct the controller's nested input paths from hash-pinned flat files."""
    directory = Path(directory)
    checked = {}
    for name, expected in INPUT_SHA256.items():
        data = (directory/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Frozen commit input changed: ' + name)
        checked[name] = data
    target = directory/'evidence/skbio-commit-intake'
    for name, data in checked.items():
        path = target/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Existing controller input differs: ' + name)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in checked.items():
        (target/name).write_bytes(data)
    return target


def main():
    started=time.monotonic()
    output=Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True,exist_ok=True)
    try:
        prepare_commit_inputs(Path(__file__).resolve().parent)
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
        command=[str(root/'.venv/bin/python'),'run_smith_controls.py','--stage','skbio-commit',
                 '--campaign','control-output','--worker-name',os.environ['BIOTASKS21_WORKER_NAME'],
                 '--source-archive','repo2rlenv-source.tar.gz']
        return capture(command,source=Path('control-output'),output=output,timeout=remaining+240,env=env)
    except Exception as exc:
        (output/'wrapper-failure.json').write_text(json.dumps({'error_type':type(exc).__name__,'stage':'setup_or_controller'}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
