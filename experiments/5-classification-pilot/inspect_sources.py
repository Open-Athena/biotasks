"""Bounded static source acquisition; never executes notebook code or downloads inputs."""
import datetime
import hashlib
import json
from pathlib import Path
import resource
import urllib.request

ROOT = Path(__file__).resolve().parent
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
records = []
for row in json.loads((ROOT / 'sample.json').read_text()):
    with urllib.request.urlopen(row['raw_url'], timeout=30) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError(f"Source exceeds 4 MiB: {row['id']}")
    if row['path'].endswith('.ipynb'):
        doc = json.loads(raw)
        chunks = [{'locator': f'cell:{i}', 'kind': c['cell_type'], 'text': ''.join(c.get('source', []))}
                  for i, c in enumerate(doc['cells'])]
    else:
        chunks = [{'locator': f'line:{i}', 'kind': 'source', 'text': s}
                  for i, s in enumerate(raw.decode().splitlines(), 1)]
    records.append({**row, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'chunks': chunks})
(ROOT / 'source-content.json').write_text(json.dumps(records, indent=2) + '\n')
(ROOT / 'acquisition.json').write_text(json.dumps({
    'start': start, 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'exit_status': 0, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'estimated_working_set_mib': 100, 'source_count': len(records),
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'sample_sha256': hashlib.sha256((ROOT / 'sample.json').read_bytes()).hexdigest(),
    'scope': 'Static source only. Outputs omitted; no source execution or biological input downloads.'
}, indent=2) + '\n')
print('Acquired', len(records), 'source documents')
