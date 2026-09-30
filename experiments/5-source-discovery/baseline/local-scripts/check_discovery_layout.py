import datetime
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path('/home/exedev/.codex/worktrees/ec20/marin')
DEST = ROOT / 'docs/experiments/bio-task-generation/01-discovery'
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert mem>=2.5*1024**3 and mem-150*1024**2>=2*1024**3 and os.getloadavg()[0]<1.5
print('start',datetime.datetime.now(datetime.UTC).isoformat(),'estimated peak 150 MiB',flush=True)
assert hashlib.sha256((DEST/'inventory.json').read_bytes()).hexdigest()=='e2cda0e700c76e37f28e619462cdbf5d2c7a81609af0c389fea49064fbe91c65'
checked=0
for path in DEST.glob('*.md'):
    text=path.read_text()
    for match in re.finditer(r'\]\(([^)\s]+)\)',text):
        link=urlsplit(match.group(1))
        if link.scheme:
            continue
        target=path.parent/unquote(link.path) if link.path else path
        assert target.is_file(), (path, match.group(1))
        if link.fragment and target.suffix=='.md':
            titles=re.findall(r'^#+\s+(.+)$',target.read_text(),re.MULTILINE)
            anchors=[re.sub(r'[^\w\- ]','',t.lower()).replace(' ','-') for t in titles]
            assert link.fragment in anchors,(path,match.group(1))
        checked+=1
print('Verified unchanged inventory bytes and',checked,'local links and anchors',flush=True)
result=subprocess.run([sys.executable, 'infra/check_docs_source_links.py'],cwd=ROOT,capture_output=True,text=True)
Path('/tmp/bio-discovery-20260929/source-link-check.txt').write_text(result.stdout+result.stderr)
print('Repository source-link check exit', result.returncode,flush=True)
print('\n'.join(result.stdout.splitlines()[:4]),flush=True)
if result.returncode:
    print(result.stdout+result.stderr)
    raise SystemExit(result.returncode)
result=subprocess.run([sys.executable,'/tmp/bio-discovery-20260929/verify_adoption.py'],cwd=ROOT)
print('end',datetime.datetime.now(datetime.UTC).isoformat(),'validation exit',result.returncode,flush=True)
raise SystemExit(result.returncode)
