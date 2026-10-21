import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
payload=Path('/tmp/biotasks19-autonomous022-thin-payload')
root=Path('/tmp/biotasks19-autonomous022-thin-extracted');root.mkdir(exist_ok=False)
manifest=json.loads((payload/'inputs.json').read_text())
assert manifest['source_archive_policy']=='autonomous-runtime-and-seed-v1'
for name,digest in manifest['files'].items():
 with (payload/name).open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==digest
with tarfile.open(payload/'biotasks.tar') as f:
 names=[m.name for m in f.getmembers() if m.isfile()]
 assert all('autonomous-runs/' not in n for n in names)
 f.extractall(root,filter='data')
exp=root/'experiments/19-repo2rlenv-notebook-pilot'
config=json.loads((payload/'campaign-config.json').read_text())
seed=json.loads((payload/'seeds.json').read_text())[0]
assert [n for n in names if n.endswith('.ipynb')]==['experiments/19-repo2rlenv-notebook-pilot/'+config['notebook_file']]
with (exp/config['notebook_file']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==seed['source_sha256']
pin=json.loads((exp/'upstream-pin.json').read_text())
for item in pin['patches']:
 assert hashlib.sha256((exp/item['path']).read_bytes()).hexdigest()==item['sha256']
env={**os.environ,'PYTHONPATH':str(root/'src')+':'+str(exp)}
modules=['run_autonomous','run_preparation','run_reference_setup','run_reference_replay','run_specification','run_notebook_grader','run_scientific_native','biotasks.chat_author']
code='import importlib,json; from pathlib import Path\nmodules='+repr(modules)+'\nroot=Path('+repr(str(root))+')\nfor name in modules:\n m=importlib.import_module(name);assert Path(m.__file__).is_relative_to(root),name\nprint(json.dumps({"runtime_imports":modules}))'
r=subprocess.run([sys.executable,'-c',code],env=env,cwd=root,capture_output=True,text=True,timeout=30)
if r.returncode:print(r.stderr);raise SystemExit(r.returncode)
print(r.stdout.strip())
subprocess.run(['/home/exedev/.codex/worktrees/7ba3/biotasks/.venv/bin/python',str(exp/'convert_seed.py'),str(exp/config['notebook_file']),str(root/'intake')],env=env,cwd=root,check=True,timeout=30)
receipt=json.loads((root/'intake/conversion.json').read_text());assert receipt['source_sha256']==seed['source_sha256']
summary={'factory_revision':manifest['factory_revision'],'archive_bytes':(payload/'biotasks.tar').stat().st_size,'prior_archive_bytes':Path('/tmp/biotasks19-autonomous022-prepared-payload/biotasks.tar').stat().st_size,'archive_policy':manifest['source_archive_policy'],'file_count':len(names),'patches_verified':len(pin['patches']),'runtime_modules_imported':modules,'source_identity_verified':True,'conversion_profile':receipt['profile'],'scientific_execution':False,'model_calls':0}
Path('/tmp/biotasks19-thin-payload-check.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
