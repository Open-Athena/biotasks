"""Read-only, bounded public source pull; no credentials, execution or datasets."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
CACHE = Path('/tmp/biotasks-16-inspection')
CACHE.mkdir(exist_ok=True)
records = []
for identifier, ref, competition in json.loads((ROOT / 'selected-kaggle.json').read_text()):
    row = dict(id=identifier, ref=ref, competition=competition,
               started_at=datetime.now(UTC).isoformat())
    try:
        url = f'https://www.kaggle.com/api/v1/kernels/pull/{ref}'
        with urlopen(url, timeout=10) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Source response exceeds 2 MB inspection cap')
        payload = json.loads(raw)
        row.update(metadata=payload['metadata'], bytes=len(raw),
                   sha256=hashlib.sha256(raw).hexdigest())
        blob = payload['blob']
        code = blob['source']
        notebook = json.loads(code)
        cells = notebook.get('cells', [])
        source = '\n'.join(''.join(c.get('source', [])) for c in cells)
        (CACHE / f'{identifier}.txt').write_text(source)
        row.update(cells=len(cells), code_cells=sum(c['cell_type']=='code' for c in cells),
                   source_sha256=hashlib.sha256(code.encode()).hexdigest(), access='source_read')
    except Exception as exc:
        row.update(access='unresolved', error=f'{type(exc).__name__}: {exc}')
    row['ended_at'] = datetime.now(UTC).isoformat()
    records.append(row)
    (ROOT / 'evidence/kaggle-documents.json').write_text(json.dumps(records, indent=2)+'\n')
    print(identifier, row['access'], row.get('error', ''), flush=True)
