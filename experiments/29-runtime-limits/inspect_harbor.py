"""Verify the historical Harbor wheel and retain only relevant source, never install it."""
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent
with urllib.request.urlopen('https://pypi.org/pypi/harbor/0.6.6/json',timeout=30) as response:
    raw=response.read(1024*1024+1)
assert len(raw)<=1024*1024
meta=json.loads(raw)
assert meta['info']['name']=='harbor' and meta['info']['version']=='0.6.6'
record=next(r for r in meta['urls'] if r['filename']=='harbor-0.6.6-py3-none-any.whl')
assert record['size']<=10*1024**2
with urllib.request.urlopen(record['url'],timeout=30) as response:
    wheel=response.read(10*1024**2+1)
assert len(wheel)==record['size'] and hashlib.sha256(wheel).hexdigest()==record['digests']['sha256']
target=ROOT/'harbor066-source';target.mkdir(exist_ok=True)
selected=[]
with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
    for name in archive.namelist():
        if name in ['harbor/cli/jobs.py','harbor/models/job/config.py','harbor/models/trial/config.py','harbor/verifier/verifier.py','harbor/trial/trial.py'] or ('dist-info/' in name and name.endswith(('LICENSE','LICENSE.txt'))):
            content=archive.read(name)
            output=target/name;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(content)
            selected.append({'path':name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
assert any(x['path'].endswith(('LICENSE','LICENSE.txt')) for x in selected), 'Retain license before publishing source'
assert any(x['path']=='harbor/cli/jobs.py' for x in selected)
report={'package':'harbor','version':'0.6.6','wheel_url':record['url'],'wheel_sha256':record['digests']['sha256'],'wheel_bytes':len(wheel),'metadata_sha256':hashlib.sha256(raw).hexdigest(),'summary':meta['info']['summary'],'selected_source_files':selected,'scope':'Read source from verified wheel, no installation/import/execution'}
(ROOT/'harbor066-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'wheel_bytes':len(wheel),'files':len(selected),'sha256_verified':True,'summary':report['summary']}))
