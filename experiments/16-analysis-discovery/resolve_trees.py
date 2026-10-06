"""Bounded metadata-only source recovery; no analysis or input execution."""
import json
import os
import subprocess
from pathlib import Path

assert os.getloadavg()[0] < 1.5
available = next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
assert available >= 2621440 and available - 65536 >= 2097152
repos = ['danforthcenter/plantcv-tutorial-v4-multiobject', 'thelovelab/DESeq2',
         'hansenlab/minfi', 'joey711/phyloseq', 'sneumann/xcms',
         'dream-olfaction/olfaction-prediction']
out = {}
for repo in repos:
    rev = json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/commits/HEAD']))['sha']
    tree = json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/git/trees/{rev}?recursive=1']))
    out[repo] = {'revision': rev, 'truncated': tree.get('truncated'),
                 'files': [{k: x[k] for k in ['path', 'sha', 'size'] if k in x}
                           for x in tree['tree'] if x['type'] == 'blob']}
    print(repo, rev, flush=True)
Path(__file__).with_name('evidence').joinpath('resolution-trees.json').write_text(json.dumps(out, indent=2)+'\n')
