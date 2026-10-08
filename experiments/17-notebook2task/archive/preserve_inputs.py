"""Retain the frozen comparison seeds; publication does not authorize reruns."""
import hashlib,json,os,tempfile
from pathlib import Path
from huggingface_hub import HfApi
import huggingface_hub
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/17-notebook2task'
SEEDS=ROOT/'downloads/notebook2task-pilot-20261006'
records=json.loads((EXP/'runs/20261006-seta-v1-pilot/input-manifest.json').read_text())
files=[]
for case in records:
 for f in case['files']:
  p=SEEDS/case['id']/'seed'/f['path']
  data=p.read_bytes()
  assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256']
  files.append({**f,'path':case['id']+'/seed/'+f['path'],'sources':case['source_urls']})
manifest={'scope':'Exact comparison seeds used in issue 17; evaluation/comparison only, not training inputs.','visibility':'public','retention':'Retain while cited; append-only snapshot, no automatic deletion on issue closure.','provenance':'Source releases and versions recorded in each file and original input-manifest.json. SETA and BixBench releases declare Apache-2.0; original Kaggle notebook remains attributed to Gabriel Preda, version 96, with generation-time version unresolved. No relicensing is implied.','files':files}
raw=(json.dumps(manifest,indent=2)+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
prefix='research/17-notebook2task/2026-10-08/'+sha
(EXP/'archive/input-snapshot-manifest.json').write_bytes(raw)
api=HfApi(token=os.environ.get('HF_TOKEN') or Path('/home/exedev/.cache/huggingface/token').read_text().strip())
existing=list(api.list_bucket_tree('open-athena/biotasks',prefix=prefix,recursive=True))
assert not existing,'Refusing overwrite; inspect partial upload before retry'
for f in files:
 api.batch_bucket_files('open-athena/biotasks',add=[(SEEDS/f['path'],prefix+'/'+f['path'])])
api.batch_bucket_files('open-athena/biotasks',add=[(raw,prefix+'/manifest.json')])
with tempfile.TemporaryDirectory(prefix='bio17-bucket-readback-') as folder:
 for f in files+[{'path':'manifest.json','bytes':len(raw),'sha256':sha}]:
  p=Path(folder)/f['path'];p.parent.mkdir(parents=True,exist_ok=True)
  api.download_bucket_files('open-athena/biotasks',[(prefix+'/'+f['path'],p)],token=False,raise_on_missing_files=True)
  data=p.read_bytes();assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256']
receipt={'bucket':'open-athena/biotasks','prefix':prefix,'uri':'hf://buckets/open-athena/biotasks/'+prefix,'manifest_sha256':sha,'files_verified':len(files),'bytes':sum(f['bytes'] for f in files),'anonymous_readback':True,'client_version':huggingface_hub.__version__}
(EXP/'archive/input-snapshot-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
