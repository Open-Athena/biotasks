"""Build the methods-first workbench from the normalized explorer data."""
from pathlib import Path
import json
import hashlib
root = Path(__file__).resolve().parent
source = (root/'explorer.html').read_text()
payload = source.split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0]
data = json.loads(payload)
data['tool_provenance'] = json.loads((root/'evidence/tool-discovery-provenance.json').read_text())
data['alternative_audit'] = json.loads((root/'alternative-source-audit/summary.json').read_text())
data['repository_audit'] = json.loads((root/'repo-notebook-audit/summary.json').read_text())
# Present one inventory; retain acquisition-specific evidence inside each record.
alt = {r['source_id']: r for r in data['alternative_audit']['rows']}
unified = []
for r in data['repository_audit']['rows']:
    a = alt.get(r['source_id'])
    if a:
        result = {'document_located':'located','tutorial_lead':'lead','none_detected':'none_detected'}[a['result']]
        docs = a['documents']
        evidence = a
        url = a['source_url']
        formats = a['formats']
        method = a['route']
    else:
        result = {'present':'located','unknown':'unknown','none_detected':'none_detected'}[r['status']]
        docs = [{**n, 'url': f"https://github.com/{r['repo']}/blob/{r['revision']}/{n['path']}", 'detection':'Repository file / signature'} for n in r['examples']]
        evidence = r
        url = 'https://github.com/' + r['repo']
        formats = r['formats']
        method = 'Repository tree and bounded text signatures'
    unified.append({'source_id':r['source_id'],'name':r['name'],'primary_domain':r['primary_domain'],'url':url,'result':result,'formats':formats,'documents':docs,'method':method,'evidence':evidence})
assert len(unified) == len({r['source_id'] for r in unified}) == 1014
statuses = ['located','lead','none_detected','unknown']
def tally(rs):
    return {'sources':len(rs), **{k:sum(r['result']==k for r in rs) for k in statuses}}
data['source_inventory'] = {'rows':unified,'all':tally(unified),'domains':{d:tally([r for r in unified if r['primary_domain']==d]) for d in sorted({r['primary_domain'] for r in unified})},'formats':sorted({f for r in unified for f in r['formats']})}
payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
(root/'workbench.html').write_text((root/'workbench.template.html').read_text().replace('__PAYLOAD__',payload))
inputs=['alternative-source-audit/summary.json','explorer.html','workbench.template.html','build_workbench.py','repo-notebook-audit/summary.json','evidence/tool-discovery-provenance.json']
(root/'workbench-sha256.json').write_text(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
print('Built methods-first workbench with full candidate metadata and repository audit')
