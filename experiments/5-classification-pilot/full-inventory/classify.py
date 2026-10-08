"""Generate source-evidenced, explicitly provisional inventory annotations."""
import bisect,collections,csv,hashlib,json,re
from pathlib import Path
from rules import FIELD,MODALITY,OP
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
REG=ROOT.parents[1]/'16-analysis-discovery/reassessment/documents.jsonl'

def rows(path):
 if path.exists():
  for line in path.open():yield json.loads(line)

def fragments(chunks,fmt):
 mode='narrative';disabled=False
 for c in chunks:
  text=c['text'];kind=c['kind'];loc=c['locator']
  if kind in ['markdown','raw']:yield loc,'narrative',text;continue
  if kind=='code':yield loc,'code',text;continue
  if (fmt in ['marimo','Percent-cell notebook'] or (fmt=='Jupytext' and chunks[0]['text'].lstrip().startswith('#'))) and loc.startswith('line:'):
   if text.lstrip().startswith('#'):yield loc,'narrative',text
   else:yield loc,'code',text
   continue
  if re.match(r'^\s*```',text):
   if mode=='narrative':mode='code';disabled=bool(re.search(r'eval\s*[=:]\s*(FALSE|false)',text))
   else:mode='narrative';disabled=False
   continue
  if re.match(r'^\s*<<.*>>=',text):mode='code';disabled=bool(re.search(r'eval\s*=\s*FALSE',text));continue
  if re.match(r'^\s*@\s*$',text):mode='narrative';disabled=False;continue
  yield loc,'disabled_code' if disabled else mode,text

def propose(chunks,fmt):
 fs=list(fragments(chunks,fmt));labels=[];indexes={}
 for group in ['narrative','code']:
  parts=[];starts=[];metadata=[];offset=0
  for loc,kind,text in fs:
   if (group=='narrative' and kind!='narrative') or (group=='code' and kind not in ['code','disabled_code']):continue
   if group=='code':text='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith(('#','%','//')))
   if not text.strip():continue
   starts.append(offset);metadata.append((loc,kind));parts.append(text);offset+=len(text)+1
  indexes[group]=('\n'.join(parts),starts,metadata)
 for facet,terms in [('scientific_field',FIELD),('modality',MODALITY),('operation',OP)]:
  text,starts,metadata=indexes['code' if facet=='operation' else 'narrative']
  for term,pattern in terms.items():
   evidence=[];seen=set();rx=re.compile(pattern,0 if facet=='operation' else re.I)
   for m in rx.finditer(text):
    loc,kind=metadata[bisect.bisect_right(starts,m.start())-1]
    if loc in seen:continue
    seen.add(loc);evidence.append({'locator':loc,'match':m.group(),'snippet':text[max(0,m.start()-65):m.end()+100].replace('\n',' '),'source_kind':kind})
    if len(evidence)==2:break
   if evidence:
    a={'facet':facet,'term':term,'status':'rule_assigned','evidence':evidence,'method':'source_narrative_pattern' if facet!='operation' else 'code_signature','review':'not_individually_adjudicated'}
    if facet=='operation':a.update(role='code_present_execution_unverified',target='requires semantic review',disabled_code=any(e['source_kind']=='disabled_code' for e in evidence))
    labels.append(a)
 return labels,fs

def main():
 acquisitions={r['document_key']:r for filename in ['acquisition.jsonl','recovery.jsonl','format-corrections.jsonl'] for r in rows(ROOT/filename)}
 pilot=json.loads((BASE/'annotations.json').read_text());pilot_by_url={r['source_url']:r for r in pilot}
 reconcile=json.loads((BASE/'registry-reconciliation.json').read_text());bykey={}
 for r in reconcile['rows']:
  if r['state']=='exact_pinned_source':
   for hit in r['matches']:
    if hit['match']=='exact_pinned_source':bykey[hit['document_key']]=next(a for a in pilot if a['id']==r['pilot_id'])
 manual={r['document_key']:r for r in rows(ROOT/'reviewed-annotations.jsonl')}
 records=[]
 from acquire import guard
 for number,d in enumerate(list(rows(REG))+list(rows(ROOT/'additional-documents.jsonl'))):
  if number%100==0:guard();print('Classified source records',number,flush=True)
  key=d['document_key'];acq=acquisitions.get(key,{});status=acq.get('status','not_yet_acquired')
  r={k:d.get(k) for k in ['document_key','url','format','repo','revision','path','source_ids']}
  r.update(acquisition_status=status,source_sha256=acq.get('sha256'),identity=acq.get('identity'),labels=[],review='not_individually_adjudicated',counted=not status.startswith('excluded_') and status!='rendered_fallback_separate',source_role='unreviewed',scope='Selected source-based labels; missing labels do not establish absence.')
  if status=='confirmed' and acq.get('content_file'):
   chunks=json.loads((ROOT/'content'/acq['content_file']).read_text())['chunks'];r['labels'],fs=propose(chunks,d['format'])
   r['title']=next((re.sub(r'<[^>]+>',' ',t).strip().strip('#').strip()[:140] for _,k,t in fs if k=='narrative' and t.strip() and not t.lstrip().startswith(('---','%','<!--'))),Path(d['path']).name)
   r['narrative_excerpt']=' '.join(t for _,k,t in fs if k=='narrative')[:1500]
  p=bykey.get(key) or pilot_by_url.get(d['url'])
  if p and acq.get('sha256')==p['source_sha256']:
   r.update(labels=p['labels'],review='assistant_individual_source_review',source_role=p.get('source_role','analysis_or_teaching_document'),pilot_id=p['id'],input_origin=p.get('input_origin'),withheld_labels=p.get('withheld_labels',[]))
  if key in manual:
   m=manual[key];assert m['source_sha256']==acq.get('sha256'),key
   r.update({k:v for k,v in m.items() if k not in ['document_key','source_sha256']})
  r['facet_states']={f:('assistant_reviewed' if r['review']=='assistant_individual_source_review' else 'rule_assigned') if any(a['facet']==f for a in r['labels']) else 'insufficient_evidence' for f in ['scientific_field','modality','operation']}
  if r.get('reviewed_facet_states',{}).get('scientific_field')=='not_applicable':r['facet_states']['scientific_field']='not_applicable'
  if status!='confirmed':r['facet_states']={f:'source_unresolved' for f in r['facet_states']}
  records.append(r)
 # Exact original-byte copies are one global document, retaining all locations.
 owners={}
 def priority(r):return (r['review']=='assistant_individual_source_review',bool(r.get('revision')),bool(r.get('repo')))
 for r in records:
  if r['counted'] and r['acquisition_status']=='confirmed' and r.get('source_sha256'):
   sha=r['source_sha256'];prior=owners.get(sha)
   if prior is None or priority(r)>priority(prior):owners[sha]=r
 for r in records:
  owner=owners.get(r.get('source_sha256')) if r['acquisition_status']=='confirmed' else None
  r['canonical_document_key']=owner['document_key'] if owner else r['document_key']
  if owner and owner is not r:
   r['counted']=False;r['duplicate_of']=owner['document_key']
   if owner['review']=='assistant_individual_source_review' and r['review']!='assistant_individual_source_review':
    r.update(labels=owner['labels'],review='assistant_review_transferred_exact_bytes',facet_states=owner['facet_states'],source_role=owner['source_role'],withheld_labels=owner.get('withheld_labels',[]))
 with (ROOT/'annotations.jsonl').open('w') as h:
  for r in records:h.write(json.dumps(r)+'\n')
 result={'records':len(records),'counted_authoring_locators':sum(r['counted'] for r in records),'acquisition_states':dict(collections.Counter(r['acquisition_status'] for r in records)),'review_states':dict(collections.Counter(r['review'] for r in records)),'facet_coverage':{f:dict(collections.Counter(r['facet_states'][f] for r in records if r['counted'])) for f in ['scientific_field','modality','operation']},'notebook_execution':False,'independent_review':False}
 (ROOT/'classification-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
