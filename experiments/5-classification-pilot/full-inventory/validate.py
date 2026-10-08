"""Validate inventory accounting, identities and classification evidence."""
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from classify import rows
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parents[1]/'16-analysis-discovery/reassessment'
def main():
 docs=list(rows(ROOT/'annotations.jsonl'));bykey={d['document_key']:d for d in docs};v=json.loads((ROOT/'vocabulary.json').read_text());s=json.loads((ROOT/'summary.json').read_text())
 assert len(bykey)==len(docs)==4301
 acq={r['document_key']:r for f in ['acquisition.jsonl','recovery.jsonl','format-corrections.jsonl'] for r in rows(ROOT/f)}
 assert set(acq)==set(bykey)
 for d in docs:
  a=acq[d['document_key']];assert a['status']==d['acquisition_status']
  assert d['source_sha256']==a.get('sha256')
  if d.get('duplicate_of'):
   owner=bykey[d['duplicate_of']];assert owner['counted'] and owner['source_sha256']==d['source_sha256'];assert not d['counted']
  if d['labels']:
   assert a['status']=='confirmed' and a.get('content_file')
   source=json.loads((ROOT/'content'/a['content_file']).read_text());locs={c['locator']:c['text'] for c in source['chunks']};assert source['sha256']==d['source_sha256']
   for label in d['labels']:
    assert label['term'] in v[label['facet']]
    assert label['status'] in v['assignment_states']
    if label['facet']=='operation':assert label['role'] in v['operation_roles'] and label['target']
    for e in label['evidence']:
     loc=e if isinstance(e,str) else e['locator'];assert loc in locs,(d['document_key'],loc)
     if isinstance(e,dict) and 'match' in e:assert e['match'] in locs[loc],(d['document_key'],e)
 assert sum(d['counted'] for d in docs)==s['authoring_locators']
 assert s['authoring_locators']==4277+15-s['excluded_format_collisions']-s['duplicate_locations']
 assert sum(s['formats'].values())==s['authoring_locators']
 repo_counts={r['repository']:int(r['notebook_count']) for r in csv.DictReader((ROOT/'repository-counts.csv').open())};expected=defaultdict(set)
 payload=json.loads((ROOT/'explorer-data.json').read_text())
 for d in payload['documents']:
  if not d['acquisition_status'].startswith('excluded_') and d['format']!='Rendered vignette':
   for repo in d['repositories']:expected[repo].add(d['canonical_document_key'])
 assert all(n==len(expected[repo]) for repo,n in repo_counts.items())
 assert sum(repo_counts.values())==s['repository_attributions']
 assert sum(n>0 for n in repo_counts.values())==s['repositories_with_documents']
 assert bykey['github:lammps/lammps:examples/PACKAGES/uf3/in.uf3.Nb']['acquisition_status']=='excluded_simulation_input'
 assert bykey['github:epam/indigo:utils/indigo-service/backend/service/tests/data/imago/imago_test_1.dib']['acquisition_status']=='excluded_bitmap'
 assert sum(d['acquisition_status']=='excluded_symlink_reference' for d in docs)==25
 assert not any(d['counted'] for d in docs if d['format']=='Rendered vignette')
 reviewed=list(rows(ROOT/'reviewed-annotations.jsonl'));assert len(reviewed)==22
 assert Counter(r['review_batch'] for r in reviewed)['contrast-C']==2 and Counter(r['review_batch'] for r in reviewed)['contrast-D']==2
 assert hashlib.sha256((OLD/'documents.jsonl').read_bytes()).hexdigest()=='9524f6e2712399b39781c6295301d68a13738fe321d3e6f829fdddedd5451fef'
 result={'passed':True,'document_records':len(docs),'distinct_authoring_documents':s['authoring_locators'],'checks':['complete acquisition accounting','unchanged baseline registry','vocabulary membership','source hash and evidence locators','code-pattern matches in original source chunk','exact-byte duplicate identity','repository attribution totals','format collision regressions','separate rendered fallbacks','final contrast records'],'semantic_validation':'No independent biological review; automated assignments remain provisional.','fingerprints':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['annotations.jsonl','vocabulary.json','rules.py','reviewed-annotations.jsonl','summary.json','repository-counts.csv','source-counts.csv','inventory.html']}}
 (ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
