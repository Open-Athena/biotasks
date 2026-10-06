"""Bounded, sequential static-source retrieval; never executes analysis code.

Optional arguments: selection JSON name, output metadata JSON name.
Responses default to a 4 MB cap; a selection can explicitly allow up to 8 MB.
Each request has a 12-second timeout. Raw sources stay in /tmp.
"""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent
CACHE=Path('/tmp/biotasks16-expansion'); CACHE.mkdir(exist_ok=True)

def fetch(url, cap):
    assert 0 < cap <= 8_000_000
    with urlopen(url,timeout=12) as r: raw=r.read(cap+1)
    if len(raw)>cap: raise ValueError(f'{cap} byte source cap exceeded')
    return raw

selection = sys.argv[1] if len(sys.argv)>1 else 'selected-expansion.json'
output = sys.argv[2] if len(sys.argv)>2 else 'expansion-documents.json'
records=[]
for item in json.loads((ROOT/selection).read_text()):
    r=dict(item, started_at=datetime.now(UTC).isoformat())
    try:
        raw=fetch(item['fetch_url'], item.get('max_bytes', 4_000_000))
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
    (ROOT/'evidence'/output).write_text(json.dumps(records,indent=2)+'\n')
    print(r['id'],r['access'],r.get('bytes'),flush=True)
