"""Link inspected versions to the frozen registry without applying labels."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parent
registry = root.parent/'16-analysis-discovery/reassessment/documents.jsonl'
annotations = json.loads((root/'annotations.json').read_text())

def identity(url):
    parts = unquote(urlsplit(url).path).strip('/').split('/')
    if urlsplit(url).netloc.lower() != 'github.com' or len(parts)<5 or parts[2]!='blob':
        return None
    return ('/'.join(parts[:2]).lower(), '/'.join(parts[4:]), parts[3])

wanted = {r['id']:identity(r['source_url']) for r in annotations}
found = {key:[] for key in wanted}
count=0
with registry.open() as handle:
    for line in handle:
        record=json.loads(line)
        if record['format']=='Rendered vignette':
            continue
        count+=1
        reps=[record,*record.get('representations',[]),*record.get('versions',[])]
        ids={identity(rep.get('url','')) for rep in reps if isinstance(rep,dict)}
        ids.discard(None)
        for key, target in wanted.items():
            if target in ids:
                found[key].append({'document_key':record['document_key'],'match':'exact_pinned_source','source_ids':record.get('source_ids',[])})
            elif any(item[:2]==target[:2] for item in ids):
                found[key].append({'document_key':record['document_key'],'match':'same_path_other_revision','source_ids':record.get('source_ids',[])})
rows=[]
for r in annotations:
    hits=found[r['id']]
    exact={h['document_key'] for h in hits if h['match']=='exact_pinned_source'}
    state='exact_pinned_source' if len(exact)==1 else 'ambiguous' if len(exact)>1 else 'revision_review_required' if hits else 'outside_frozen_registry'
    rows.append({'pilot_id':r['id'],'source_url':r['source_url'],'state':state,'matches':hits})
result={'registry_sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),'annotation_sha256':hashlib.sha256((root/'annotations.json').read_bytes()).hexdigest(),'registry_authoring_documents':count,'pilot_documents':len(rows),'states':dict(Counter(r['state'] for r in rows)),'rows':rows,'labels_applied':False,'caveat':'Exact pinned-source identity establishes annotation applicability to that source version, not independent scientific validation. Revision differences require content review. Records absent from this frozen project inventory remain in the separate candidate pool.'}
(root/'registry-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['states'])
