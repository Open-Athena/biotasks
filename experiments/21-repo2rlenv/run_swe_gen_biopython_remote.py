"""Remote Biopython SWE-gen with bounded full-source evidence capture."""
import hashlib,json,os,subprocess,tarfile,time
started=time.monotonic()
from pathlib import Path
from preserve_author_output import preserve
from capture_author_process import capture
from iris.client.client import iris_ctx
from iris.cluster.types import JobName
capture_dir=Path(os.environ['IRIS_OUTPUT_DIR']);capture_dir.mkdir(parents=True,exist_ok=True)
root=None
try:
 source=Path('repo2rlenv-source.tar.gz')
 assert hashlib.sha256(source.read_bytes()).hexdigest()=='7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
 r=iris_ctx().client.resolver_for_job(JobName.from_string('/muchanem/glm53-relay-rno2a')).resolve('glm-5.3')
 if not r.endpoints:raise RuntimeError('Approved relay unavailable')
 endpoint=r.endpoints[0].url.rstrip('/')
 if not endpoint.endswith('/v1'):endpoint+='/v1'
 with tarfile.open(source) as t:t.extractall('r2e',filter='data')
 roots=list(Path('r2e').iterdir());assert len(roots)==1;root=roots[0]
 env=dict(os.environ);env.pop('VIRTUAL_ENV',None);env['UV_PROJECT_ENVIRONMENT']=str(root.resolve()/'.venv')
 subprocess.run(['uv','sync','--frozen','--no-dev','--extra','harbor','--extra','daytona','--python','3.12.3','--project',str(root)],env=env,check=True,timeout=600)
 subprocess.run(['uv','build','--wheel','--project',str(root)],env=env,check=True,timeout=300)
 wheels=list((root/'dist').glob('*.whl'));assert len(wheels)==1
 remaining=int(6900-(time.monotonic()-started))
 if remaining<900:raise TimeoutError('Insufficient remaining generation window')
 env.update(REPO2RLENV_MODEL_WORKER='1',BIOTASKS21_GLM_ENDPOINT=endpoint,BIOTASKS21_CONTROLLER_DEADLINE=str(remaining))
 args=[str(root/'.venv/bin/python'),'run_swe_gen_controller.py','--campaign','author-output','--wheel',str(wheels[0]),'--profile','swe-gen-biopython-profile.json','--adaptation','glm-generation-adaptation.json','--worker-name','biotasks21-swe-gen-biopython-01','--source','source.json','--source-sha256',os.environ['BIOTASKS21_SOURCE_SHA256']]
 code=capture(args,source=Path('author-output'),output=capture_dir/'child',env=env,timeout=remaining+240,maximum_bytes=2*1024**3)

 (capture_dir/'wrapper-status.json').write_text(json.dumps({'stage':'history_selection_contrast_author_export','child_exit_code':code}))
 raise SystemExit(code)
except Exception as exc:
 (capture_dir/'wrapper-status.json').write_text(json.dumps({'stage':'setup_or_controller','error_type':type(exc).__name__}))
 raise SystemExit(1)

finally:
 if Path('author-output').is_dir() and not (capture_dir/'after-cleanup/author-evidence.tar.gz').exists():
  preserve(Path('author-output'),capture_dir/'wrapper-fallback',max_bytes=2*1024**3)
