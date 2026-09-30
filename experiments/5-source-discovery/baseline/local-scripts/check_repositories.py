import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/tmp/bio-discovery-20260929')
data = json.loads((ROOT/'inventory-draft.json').read_text())
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))) * 1024
assert mem >= 2.5*1024**3 and mem-100*1024**2 >= 2*1024**3 and os.getloadavg()[0] < 1.5
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated working set 100 MiB', flush=True)
checked = 0
for record in data['repositories']:
    url = record['repository_url']
    if not url or not url.startswith('https://github.com/'):
        continue
    mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                   if line.startswith('MemAvailable:'))) * 1024
    if mem < 2*1024**3 or os.getloadavg()[0] > 2.5:
        raise RuntimeError('Node resource threshold reached')
    slug = url.removeprefix('https://github.com/').rstrip('/')
    metadata = json.loads(subprocess.check_output(['gh', 'api', f'repos/{slug}'], timeout=20))
    record['repository_url'] = metadata['html_url']
    record['github_metadata'] = {key: metadata[key] for key in (
        'full_name', 'default_branch', 'archived', 'fork', 'stargazers_count', 'pushed_at', 'license')}
    record['github_metadata']['source_url'] = f'https://api.github.com/repos/{slug}'
    record['github_metadata']['observed_on'] = '2026-09-29'
    if metadata['archived']:
        record['notes'].append('Repository is archived; assess maintenance and successors.')
    if metadata['fork']:
        record['notes'].append('GitHub identifies this repository as a fork; resolve upstream before deep inspection.')
    if metadata.get('homepage'):
        record['documentation_urls'] = list(dict.fromkeys(record['documentation_urls']+[metadata['homepage']]))
    checked += 1
    if checked%10 == 0:
        print('checked', checked, flush=True)
(ROOT/'inventory-checked.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
print('end', datetime.datetime.now(datetime.UTC).isoformat(), 'checked', checked, flush=True)
