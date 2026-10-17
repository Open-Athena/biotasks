"""Remote SETA Evol materialization with supported child-output capture."""
import hashlib,json,os,subprocess,tarfile,time
started=time.monotonic()
from pathlib import Path
from package_provider_task import unpack
from preserve_author_output import preserve
from capture_author_process import capture
from iris.client.client import iris_ctx
from iris.cluster.types import JobName
capture_dir=Path(os.environ['IRIS_OUTPUT_DIR']);capture_dir.mkdir(parents=True,exist_ok=True)
root=None
try:
 unpack(Path('parent-bundle.tar.gz'),Path('parent-bundle-manifest.json'),Path('.'))
 Path('task').rename('parent')
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
 code=capture([str(root/'.venv/bin/python'),'run_parent_evolution_build.py','--campaign','author-output','--wheel',str(wheels[0]),'--parent','parent','--manifest','parent-manifest.json','--adaptation','glm-generation-adaptation.json','--worker-name','biotasks21-parent-evolution-build-01','--designs','saved-designs.json','--designs-sha256','31f6a464514836d4b4ff3d4fdaeca9bc3db3bd105c7c3e3d94dfb2cccc041971'],source=Path('author-output'),output=capture_dir/'child',env=env,timeout=remaining+240)
 (capture_dir/'wrapper-status.json').write_text(json.dumps({'stage':'seta_evol_build_repair_trial_export','child_exit_code':code}))
 raise SystemExit(code)
except Exception as exc:
 (capture_dir/'wrapper-status.json').write_text(json.dumps({'stage':'setup_or_controller','error_type':type(exc).__name__}))
 raise SystemExit(1)

finally:
 if Path('author-output').is_dir() and not (capture_dir/'after-cleanup/author-evidence.tar.gz').exists():
  preserve(Path('author-output'),capture_dir/'wrapper-fallback')
