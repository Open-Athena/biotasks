"""Second-pass static sources only: bounded to 12 selected files, no execution."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent
CACHE=Path('/tmp/biotasks16-expansion'); CACHE.mkdir(exist_ok=True)

def fetch(url):
    with urlopen(url,timeout=12) as r: raw=r.read(4_000_001)
    if len(raw)>4_000_000: raise ValueError('4 MB source cap exceeded')
    return raw

records=[]
for item in json.loads((ROOT/'selected-expansion.json').read_text()):
    r=dict(item, started_at=datetime.now(UTC).isoformat())
    try:
        raw=fetch(item['fetch_url'])
        r.update(bytes=len(raw),response_sha256=hashlib.sha256(raw).hexdigest())
        source=raw.decode()
        if item['kind']=='kaggle':
            data=json.loads(source);r['metadata']=data['metadata']; source=data['blob']['source']
        r['source_sha256']=hashlib.sha256(source.encode()).hexdigest()
        if item['kind'] in ['ipynb','kaggle']:
            cells=json.loads(source)['cells'];r['cells']=len(cells)
            r['code_cells']=sum(c['cell_type']=='code' for c in cells)
            source='\n'.join(''.join(c.get('source',[])) for c in cells)
        (CACHE/(item['id']+'.txt')).write_text(source)
        r['access']='source_read'
    except Exception as e:r.update(access='unresolved',error=f'{type(e).__name__}: {e}')
    r['ended_at']=datetime.now(UTC).isoformat();records.append(r)
    (ROOT/'evidence/expansion-documents.json').write_text(json.dumps(records,indent=2)+'\n')
    print(r['id'],r['access'],r.get('bytes'),flush=True)
