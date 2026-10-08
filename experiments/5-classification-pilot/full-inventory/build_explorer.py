"""Build an offline explorer with separate reviewed and rule-assigned evidence."""
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import unquote,urlsplit
from rules import FIELD
from classify import propose,rows
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parents[1]/'16-analysis-discovery/reassessment'
ALIASES=json.loads((OLD/'adjudications.json').read_text()).get('repository_aliases',{})
def canon(repo):
 repo=repo.lower();seen=set()
 while repo in ALIASES and repo not in seen:seen.add(repo);repo=ALIASES[repo]
 return repo

def repourl(url):
 parts=unquote(urlsplit(url).path).strip('/').split('/')
 if urlsplit(url).hostname in ['github.com','www.github.com'] and len(parts)>4 and parts[2]=='blob':return canon('/'.join(parts[:2]))
 return None

def main():
 docs=list(rows(ROOT/'annotations.jsonl'));old={d['document_key']:d for d in rows(OLD/'documents.jsonl')}
 counts=list(csv.DictReader((OLD/'repository-counts.csv').open()));repos={r['repository']:{'repository':r['repository'],'notebook_count':int(r['notebook_count']),'baseline_count':int(r['notebook_count']),'labels':[],'review':'not_reviewed','source_url':None} for r in counts}
 repo_documents=defaultdict(set)
 for d in docs:
  targets={x for x in [repourl(d['url']),*[repourl(r.get('url','')) for r in old.get(d['document_key'],{}).get('representations',[])]] if x}
  d['repositories']=sorted(targets)
  if not d['acquisition_status'].startswith('excluded_') and d['format']!='Rendered vignette':
   for repo in targets:
    repos.setdefault(repo,{'repository':repo,'notebook_count':0,'baseline_count':0,'labels':[],'review':'not_reviewed','source_url':None})
    repo_documents[repo].add(d['canonical_document_key'])
 for repo,r in repos.items():r['notebook_count']=len(repo_documents[repo])
 for r in rows(ROOT/'repository-acquisition.jsonl'):
  repo=r['repository'];target=repos.get(repo)
  if target is None:continue
  target['acquisition_status']=r['status'];target['source_url']=r.get('url');target['sha256']=r.get('sha256')
  if r.get('content_file'):
   text=json.loads((ROOT/'content'/r['content_file']).read_text())['text']
   labels,_=propose([{'locator':f'line:{i+1}','text':t,'kind':'markdown'} for i,t in enumerate(text.splitlines())],'README')
   target['labels']=[a for a in labels if a['facet']=='scientific_field'];target['review']='rule_assigned_readme_scope'
  else:target['review']='readme_unavailable'
 for r in json.loads((ROOT.parent/'repository-annotations.json').read_text()):
  repo=canon(r['repository']);target=repos.get(repo)
  if target is None:continue
  # Preserve independently reviewed pinned scope even if a newer README was fetched.
  target.update(review='assistant_individual_readme_review',review_state=r['status'],source_url=r['source_url'],sha256=r['source_sha256'],labels=[{'facet':'scientific_field','term':t,'status':'content_supported','evidence':[{'snippet':r['evidence_anchor'],'rationale':r['rationale']}]} for t in r['scientific_fields']])
 field_docs=defaultdict(set)
 for d in docs:
  if d['counted']:
   for a in d['labels']:
    if a['facet']=='scientific_field':field_docs[a['term']].add(d['document_key'])
 summary={'baseline_authoring_locators':4277,'new_candidate_documents':sum(d['document_key'] not in old for d in docs),'duplicate_locations':sum('duplicate_of' in d for d in docs),'excluded_format_collisions':sum(d['acquisition_status'].startswith('excluded_') for d in docs),'authoring_locators':sum(d['counted'] for d in docs),'rendered_fallbacks':sum(d['format']=='Rendered vignette' for d in docs),'repositories':len(repos),'repositories_with_documents':sum(r['notebook_count']>0 for r in repos.values()),'repository_attributions':sum(r['notebook_count'] for r in repos.values()),'formats':dict(Counter(d['format'] for d in docs if d['counted'])),'document_acquisition_states':dict(Counter(d['acquisition_status'] for d in docs)),'document_review_states':dict(Counter(d['review'] for d in docs)),'field_counts_including_provisional':{k:len(v) for k,v in field_docs.items()},'classification_note':'Rule assignments are provisional source-pattern classifications, separately visible from individual assistant review. No execution or independent semantic validation. Unresolved locators remain counted as historical discoveries pending confirmation; proven non-notebooks are excluded.'}
 (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 with (ROOT/'repository-counts.csv').open('w') as h:
  w=csv.DictWriter(h,fieldnames=['repository','notebook_count','baseline_count','review','source_url']);w.writeheader();w.writerows({k:r.get(k) for k in w.fieldnames} for r in repos.values())
 with (ROOT/'source-counts.csv').open('w') as h:
  source_docs=defaultdict(set)
  for d in docs:
   if not d['acquisition_status'].startswith('excluded_') and d['format']!='Rendered vignette':
    for source in d['source_ids']:source_docs[source].add(d['canonical_document_key'])
  c={s:len(keys) for s,keys in source_docs.items()};w=csv.writer(h);w.writerow(['source_id','notebook_count'])
  oldsources=list(csv.DictReader((OLD/'source-counts.csv').open()));seen=set()
  for r in oldsources:w.writerow([r['source_id'],c.get(r['source_id'],0)]);seen.add(r['source_id'])
  for key in c.keys()-seen:w.writerow([key,c[key]])
 data={'summary':summary,'documents':docs,'repositories':list(repos.values()),'vocabulary':json.loads((ROOT/'vocabulary.json').read_text())}
 (ROOT/'explorer-data.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
 template=(ROOT/'explorer.template.html').read_text();payload=json.dumps(data,separators=(',',':')).replace('<','\\u003c')
 (ROOT/'inventory.html').write_text(template.replace('__DATA__',payload))
 print({k:v for k,v in summary.items() if not isinstance(v,dict)})
if __name__=='__main__':main()
