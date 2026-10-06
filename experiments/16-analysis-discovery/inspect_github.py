"""Bounded static retrieval; never execute notebook cells. Run with shared lock."""

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
CACHE = Path('/tmp/biotasks-16-inspection')
CACHE.mkdir(exist_ok=True)


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path]))


records = []
repos = {}
for identifier, repo, path in json.loads((ROOT / 'selected-github.json').read_text()):
    start = datetime.now(UTC).isoformat()
    if repo not in repos:
        metadata = api(f'repos/{repo}')
        revision = api(f'repos/{repo}/commits/HEAD')['sha']
        tree = api(f'repos/{repo}/git/trees/{revision}?recursive=1')
        repos[repo] = (metadata, revision, tree)
    metadata, revision, tree = repos[repo]
    entry = next(x for x in tree['tree'] if x['path'] == path)
    assert entry['size'] < 5_000_000
    url = f'https://raw.githubusercontent.com/{repo}/{revision}/{quote(path)}'
    with urlopen(url, timeout=30) as response:
        raw = response.read(5_000_001)
    assert len(raw) <= 5_000_000
    notebook = json.loads(raw)
    source = '\n'.join(''.join(c.get('source', [])) for c in notebook['cells'])
    (CACHE / f'{identifier}.txt').write_text(source)
    record = dict(id=identifier, repo=repo, path=path, revision=revision,
                  url=f'https://github.com/{repo}/blob/{revision}/{quote(path)}',
                  blob_sha=entry['sha'], sha256=hashlib.sha256(raw).hexdigest(),
                  bytes=len(raw), cells=len(notebook['cells']),
                  code_cells=sum(c['cell_type'] == 'code' for c in notebook['cells']),
                  stars=metadata['stargazers_count'], license=metadata.get('license'),
                  started_at=start, ended_at=datetime.now(UTC).isoformat(),
                  input_urls=sorted(set(re.findall(r'https?://[^\s\"\)<>]+', source))))
    records.append(record)
    print(identifier, record['code_cells'], record['stars'], revision, flush=True)
(ROOT / 'evidence/github-documents.json').write_text(json.dumps(records, indent=2)+'\n')
(ROOT / 'evidence/github-trees.json').write_text(json.dumps({k: {'revision': v[1], 'truncated': v[2]['truncated'], 'tree': v[2]['tree']} for k, v in repos.items()}, indent=2)+'\n')
