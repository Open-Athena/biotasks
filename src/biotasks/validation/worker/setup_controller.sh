#!/usr/bin/env bash
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git ca-certificates
python -m pip install --no-cache-dir uv==0.11.31
python - <<'PY'
import hashlib,json,urllib.request
from pathlib import Path
pins=json.loads(Path('/work/family.json').read_text())['tools']
for name in ['harbor','tenacity']:
 path=Path('/work',name+'.whl')
 with urllib.request.urlopen(pins[name+'_wheel_url'],timeout=120) as src,path.open('wb') as dst:
  total=0
  while chunk:=src.read(1024*1024):
   total+=len(chunk);assert total<8*1024**2;dst.write(chunk)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==pins[name+'_wheel_sha256']
 path.rename('/work/'+pins[name+'_wheel_filename'])
PY
uv venv --python /usr/local/bin/python /work/harbor066
uv pip install --python /work/harbor066/bin/python /work/harbor-0.6.6-py3-none-any.whl /work/tenacity-9.2.1-py3-none-any.whl
/work/harbor066/bin/harbor --version
uv pip freeze --python /work/harbor066/bin/python > /work/evidence/harbor066-freeze.txt
/work/harbor066/bin/python - <<'PY'
import hashlib,json,sysconfig,zipfile
from pathlib import Path
pins=json.loads(Path('/work/family.json').read_text())['tools']
root=Path(sysconfig.get_paths()['purelib'])
result={}
for name in ['harbor','tenacity']:
 rows={}
 with zipfile.ZipFile('/work/'+pins[name+'_wheel_filename']) as wheel:
  for item in wheel.infolist():
   if item.is_dir() or not (item.filename.endswith('.py') or '.dist-info/' in item.filename):continue
   if item.filename.endswith('/RECORD'):continue
   original=wheel.read(item)
   installed=(root/item.filename).read_bytes()
   if original!=installed:raise RuntimeError('Installed wheel source changed: '+item.filename)
   rows[item.filename]=hashlib.sha256(original).hexdigest()
 if not rows:raise RuntimeError('No wheel sources verified')
 result[name]={'wheel_sha256':pins[name+'_wheel_sha256'],'files':rows,'verified':True}
Path('/work/evidence/native-source-parity.json').write_text(json.dumps(result,indent=2)+'\n')
PY
