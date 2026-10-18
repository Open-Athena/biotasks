"""Reproduce native dependencies, then run the no-model Docker availability probe."""
import hashlib
import os
import subprocess
import tarfile
from pathlib import Path


def main():
    source=Path('repo2rlenv-source.tar.gz')
    with source.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()=='7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
    with tarfile.open(source) as archive:archive.extractall('runtime',filter='data')
    roots=list(Path('runtime').iterdir());assert len(roots)==1;root=roots[0]
    env=dict(os.environ);env.pop('VIRTUAL_ENV',None);env['UV_PROJECT_ENVIRONMENT']=str(root.resolve()/'.venv');env['LITELLM_LOCAL_MODEL_COST_MAP']='True'
    out=Path(os.environ['IRIS_OUTPUT_DIR']);out.mkdir(parents=True,exist_ok=True)
    with (out/'dependency-setup.log').open('w') as log:
        subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor','--extra','daytona','--python','3.12.3','--project',str(root)],env=env,stdout=log,stderr=log,check=True,timeout=600)
    return subprocess.run([str(root/'.venv/bin/python'),'probe_native_equivalence_backend.py'],env=env,check=False,timeout=60).returncode


if __name__=='__main__':raise SystemExit(main())
