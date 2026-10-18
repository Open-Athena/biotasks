"""Bounded no-model native similarity cohort on the approved provider."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path
from capture_author_process import capture


def main():
    started=time.monotonic();output=Path(os.environ['IRIS_OUTPUT_DIR']);output.mkdir(parents=True,exist_ok=True)
    try:
        contract=json.loads(Path('cohort-transfer.json').read_text());source=Path('cohort-tasks.tar.gz')
        assert source.stat().st_size==contract['bytes']
        with source.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==contract['sha256']
        total=0
        with tarfile.open(source) as archive:
            for member in archive:
                path=Path(member.name);assert not path.is_absolute() and '..' not in path.parts
                assert member.isfile() or member.isdir()
                total+=member.size;assert total<=16*1024**2
            archive.extractall('.',filter='data')
        native=Path('repo2rlenv-source.tar.gz')
        with native.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()=='7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
        with tarfile.open(native) as archive:archive.extractall('runtime',filter='data')
        roots=list(Path('runtime').iterdir());assert len(roots)==1;root=roots[0]
        env=dict(os.environ);env.pop('VIRTUAL_ENV',None)
        for key in list(env):
            if key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','BIOTASKS21_GLM_KEY') or key.startswith(('REPO2RLENV_JUDGE','R2E_JUDGE')):env.pop(key)
        env.update(UV_PROJECT_ENVIRONMENT=str(root.resolve()/'.venv'),LITELLM_LOCAL_MODEL_COST_MAP='True')
        with (output/'dependency-setup.log').open('w') as log:
            subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor','--extra','daytona','--python','3.12.3','--project',str(root)],env=env,stdout=log,stderr=log,check=True,timeout=600)
        remaining=int(1800-(time.monotonic()-started))
        if remaining<300:raise TimeoutError('Insufficient remaining cohort window')
        env.update(REPO2RLENV_MODEL_WORKER='1',BIOTASKS21_PREFLIGHT_REMAINING_SEC=str(remaining))
        return capture([str(root/'.venv/bin/python'),'run_prdiff_provider_controls.py','--cohort','cohort.json','--output','provider-output'],source=Path('provider-output'),output=output,timeout=remaining+240,env=env)
    except Exception as exc:
        (output/'wrapper-failure.json').write_text(json.dumps({'stage':'setup_or_cohort','error_type':type(exc).__name__}))
        return 1


if __name__=='__main__':raise SystemExit(main())
