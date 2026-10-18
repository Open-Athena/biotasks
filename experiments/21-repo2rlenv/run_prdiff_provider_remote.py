"""Bounded no-model native similarity cohort on the approved provider."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path
from capture_author_process import capture


def main(*, mode='controls'):
    if mode not in ('controls','blind'):raise ValueError('Unreviewed execution mode')
    started=time.monotonic();output=Path(os.environ['IRIS_OUTPUT_DIR']);output.mkdir(parents=True,exist_ok=True)
    try:
        if mode=='blind':
            for name in ('controls.json','acceptance.json'):
                if not Path(name).is_file():raise FileNotFoundError('Missing runtime acceptance evidence')
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
            if key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY') or (key=='BIOTASKS21_GLM_KEY' and mode=='controls') or key.startswith(('REPO2RLENV_JUDGE','R2E_JUDGE')):env.pop(key)
        env.update(UV_PROJECT_ENVIRONMENT=str(root.resolve()/'.venv'),LITELLM_LOCAL_MODEL_COST_MAP='True')
        with (output/'dependency-setup.log').open('w') as log:
            subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor','--extra','daytona','--python','3.12.3','--project',str(root)],env=env,stdout=log,stderr=log,check=True,timeout=600)
        remaining=int((1800 if mode=='controls' else 7200)-(time.monotonic()-started))
        if remaining<300:raise TimeoutError('Insufficient remaining cohort window')
        env.update(REPO2RLENV_MODEL_WORKER='1',BIOTASKS21_PREFLIGHT_REMAINING_SEC=str(remaining))
        if mode=='controls':
            command=[str(root/'.venv/bin/python'),'run_prdiff_provider_controls.py','--cohort','cohort.json','--output','provider-output'];result_dir='provider-output'
        else:
            from iris.client.client import iris_ctx
            from iris.cluster.types import JobName
            resolved=iris_ctx().client.resolver_for_job(JobName.from_string(os.environ['BIOTASKS21_GLM_RELAY_JOB'])).resolve('glm-5.3')
            if not resolved.endpoints:raise RuntimeError('Approved free GLM unavailable')
            endpoint=resolved.endpoints[0].url.rstrip('/')
            env['BIOTASKS21_GLM_ENDPOINT']=endpoint if endpoint.endswith('/v1') else endpoint+'/v1'
            command=[str(root/'.venv/bin/python'),'run_prdiff_blind_solver.py','--cohort','cohort.json','--controls','controls.json','--acceptance','acceptance.json','--output','solver-output'];result_dir='solver-output'
        return capture(command,source=Path(result_dir),output=output,timeout=remaining+240,env=env)
    except Exception as exc:
        (output/'wrapper-failure.json').write_text(json.dumps({'stage':'setup_or_cohort','error_type':type(exc).__name__}))
        return 1


if __name__=='__main__':raise SystemExit(main())
