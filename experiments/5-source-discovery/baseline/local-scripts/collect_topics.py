import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/tmp/bio-discovery-20260929/adoption')
INVENTORY = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments/bio-repository-inventory.json')
mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
assert mem >= 2.5*1024**3 and mem - 100*1024**2 >= 2*1024**3 and os.getloadavg()[0] < 1.5
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated peak 100 MiB', flush=True)
data = json.loads(INVENTORY.read_text())
repos = [r for r in data['candidates'] if r.get('github_metadata')]
query = 'query {\n'
for i,r in enumerate(repos):
    owner, name = r['github_metadata']['full_name'].split('/')
    query += f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ nameWithOwner url repositoryTopics(first: 100) {{ totalCount pageInfo {{ hasNextPage }} nodes {{ topic {{ name }} }} }} }}\n'
query += '}\n'
request_path = ROOT / 'topics-query.json'
request_path.write_text(json.dumps({'query':query}))
payload = subprocess.check_output(['gh', 'api', 'graphql', '--input', str(request_path)], timeout=45)
response = json.loads(payload)
assert not response.get('errors'), response.get('errors')
(ROOT / 'topics-response.json').write_bytes(payload)
rows=[]
for i,r in enumerate(repos):
    repo = response['data'][f'r{i}']
    assert repo is not None, r['name']
    topics = repo['repositoryTopics']
    assert not topics['pageInfo']['hasNextPage']
    tags = sorted(x['topic']['name'] for x in topics['nodes'])
    assert len(tags)==topics['totalCount']==len(set(tags))
    rows.append({'name':r['name'], 'repository_url':repo['url'], 'full_name':repo['nameWithOwner'], 'topics':tags, 'observed_on':'2026-09-29', 'source_url':'https://api.github.com/graphql', 'query_field':'repository.repositoryTopics', 'response_sha256':hashlib.sha256(payload).hexdigest()})
(ROOT / 'topics-mappings.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
    print(row['name']+': '+', '.join(row['topics']), flush=True)
print('end',datetime.datetime.now(datetime.UTC).isoformat(),'repositories',len(rows),flush=True)
