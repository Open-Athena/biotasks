"""Resolve extension collisions and symlink references using pinned Git-tree modes."""
import ast,hashlib,json,posixpath
from pathlib import Path
from collections import defaultdict
from classify import rows
ROOT=Path(__file__).resolve().parent
OLD=Path('/tmp/biotasks16-reassessment-cache-01a1183d')
latest={r['document_key']:r for f in ['acquisition.jsonl','recovery.jsonl'] for r in rows(ROOT/f)}
groups=defaultdict(list)
for r in latest.values():
 if r.get('repo') and r.get('revision'):groups[(r['repo'],r['revision'])].append(r)
out=[];checks=[]
for (repo,rev),records in groups.items():
 url=f'https://api.github.com/repos/{repo}/git/trees/{rev}?recursive=1';path=OLD/hashlib.sha256(url.encode()).hexdigest()
 if not path.exists():continue
 tree=json.loads(path.read_text());modes={e['path']:e for e in tree.get('tree',[])}
 for r in records:
  entry=modes.get(r['path'])
  if not entry or entry.get('mode')!='120000':continue
  correction=dict(r);correction.update(status='excluded_symlink_reference',tree_evidence={'url':url,'response_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':'120000','blob_sha':entry['sha']})
  preview=r.get('prefix_preview','')
  target=None
  if preview:
   try:target=ast.literal_eval(preview).decode().strip()
   except (ValueError,SyntaxError,AttributeError):pass
  if target:
   resolved=posixpath.normpath(posixpath.join(posixpath.dirname(r['path']),target));targetkey=f'github:{repo.lower()}:{resolved}'
   correction.update(link_payload=target,target_path=resolved,target_in_registry=targetkey in latest,target_document_key=targetkey)
  out.append(correction)
# Source text inspected during recovery: a benchmark Python script, no cell markers.
key='github:soft-matter/trackpy:benchmarks/maxima_benchmarks.ipynb'
r=latest[key];assert r['prefix_preview'].startswith("b'# must be run in ipython")
correction=dict(r);correction.update(status='excluded_plain_script',rationale='Plain Python benchmark script, no Jupyter JSON; suffix alone was the original detection.')
out.append(correction)
(ROOT/'format-corrections.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in out))
print('Format corrections:',len(out),'including',sum(r['status']=='excluded_symlink_reference' for r in out),'Git symlink references')
