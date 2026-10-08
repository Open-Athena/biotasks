"""Bounded static source acquisition; never executes notebooks or downloads inputs."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import urllib.request

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--sample', default='sample.json')
parser.add_argument('--prefix', default='')
args = parser.parse_args()
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
records, errors = [], []
for row in json.loads((ROOT / args.sample).read_text()):
    mem = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    load = float(Path('/proc/loadavg').read_text().split()[0])
    if mem < 2 * 1024 * 1024 or load > 2.5:
        errors.append({'id':row['id'],'error':'Shared-resource stop threshold reached'})
        break
    try:
        cap = row.get('max_source_bytes', 4 * 1024 * 1024)
        with urllib.request.urlopen(row['raw_url'], timeout=30) as response:
            raw = response.read(cap + 1)
        if len(raw) > cap:
            raise ValueError('Source exceeds configured cap')
        if row['path'].endswith('.ipynb'):
            doc = json.loads(raw)
            chunks = [{'locator': f'cell:{i}', 'kind': c['cell_type'], 'text': ''.join(c.get('source', []))}
                      for i, c in enumerate(doc['cells'])]
        else:
            chunks = [{'locator': f'line:{i}', 'kind': 'source', 'text': text}
                      for i, text in enumerate(raw.decode().splitlines(), 1)]
        records.append({**row, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'chunks': chunks})
    except Exception as exc:
        errors.append({'id':row['id'],'error':str(exc),'url':row['raw_url']})
(ROOT / (args.prefix + 'source-content.json')).write_text(json.dumps(records, indent=2) + '\n')
(ROOT / (args.prefix + 'acquisition.json')).write_text(json.dumps({
    'start': start, 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'exit_status': 1 if errors else 0, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'estimated_working_set_mib': 150, 'source_count': len(records), 'errors':errors,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'sample_sha256': hashlib.sha256((ROOT / args.sample).read_bytes()).hexdigest(),
    'scope': 'Static source only. Outputs omitted; no source execution or biological input downloads.'
}, indent=2) + '\n')
print('Acquired', len(records), 'source documents;', len(errors), 'errors')
raise SystemExit(1 if errors else 0)
