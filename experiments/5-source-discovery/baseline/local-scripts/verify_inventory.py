import csv
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

start = datetime.datetime.now(datetime.UTC).isoformat()
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))) * 1024
assert mem >= 2.5*1024**3 and mem-100*1024**2 >= 2*1024**3 and os.getloadavg()[0] < 1.5
root = Path('/tmp/bio-discovery-20260929')
path = Path('docs/experiments/bio-repository-inventory.json')
data = json.loads(path.read_text())
records = data['candidates']
with (root/'bioconda-packages.tsv').open() as handle:
    bioconda = {row['package']: int(row['total']) for row in csv.DictReader(handle, delimiter='\t')}
with (root/'bioconductor-scores.tsv').open() as handle:
    bioconductor = {row['Package']: int(row['Download_score']) for row in csv.DictReader(handle, delimiter='\t')}
resolved = [row for row in records if row['repository_url']]
assert len(records) == 95 and len(resolved) == 93
assert len({row['repository_url'].lower().rstrip('/') for row in resolved}) == 93
assert sum(row['previous_inventory_rank'] is not None for row in records) == 50
assert sum(row['previous_inventory_rank'] is None for row in resolved) == 43
assert sum('github_metadata' in row for row in records) == 65
assert sum('bioconductor_metadata' in row for row in records) == 25
assert sum((row['repository_url'] or '').startswith('https://gitlab.com/') for row in records) == 3
for row in records:
    for package in row['bioconda_packages']:
        assert package['cumulative_downloads'] == bioconda[package['name']]
    if row['bioconductor_package']:
        assert row['bioconductor_download_score'] == bioconductor[row['bioconductor_package']]
    assert all(url.startswith(('https://', 'http://')) and '{{' not in url for url in row['documentation_urls']), row['name']
for source, filename in zip(data['sources'][:3], ['bioconda-packages.tsv', 'bioconductor-scores.tsv', 'bioconductor-VIEWS']):
    assert source['sha256'] == hashlib.sha256((root/filename).read_bytes()).hexdigest()
markdown = Path('docs/experiments/computational_biology_bioinformatics_packages.md').read_text()
for row in resolved:
    assert f"[{row['name']}]({row['repository_url']})" in markdown
assert len(re.findall(r'^\| \[', markdown, re.M)) == 93
print(json.dumps({'start': start, 'end': datetime.datetime.now(datetime.UTC).isoformat(),
                  'entries': 95, 'unique_repository_links': 93, 'retained': 50,
                  'new_repository_links': 43, 'unresolved_source_leads': 2,
                  'metric_and_source_hash_checks': 'passed'}))
