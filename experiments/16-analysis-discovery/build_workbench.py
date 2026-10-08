"""Build the methods-first workbench from the normalized explorer data."""
from pathlib import Path
import json
import hashlib
from consolidate_documents import consolidate
root = Path(__file__).resolve().parent
source = (root/'explorer.html').read_text()
payload = source.split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0]
data = json.loads(payload)
data['tool_provenance'] = json.loads((root/'evidence/tool-discovery-provenance.json').read_text())
data['alternative_audit'] = json.loads((root/'alternative-source-audit/summary.json').read_text())
data['repository_audit'] = json.loads((root/'repo-notebook-audit/summary.json').read_text())
# Reassessment reconciles every route and counts complete recorded observations.
reassessment = json.loads((root/'reassessment/summary.json').read_text())
assert reassessment['completed_source_ledgers'] == 1014
# Join only independently inspected scope of the original mapped repository.
# Notebook labels and linked tutorial repositories do not define parent scope.
classification_path = root.parent/'5-classification-pilot/full-inventory/explorer-data.json'
classification = json.loads(classification_path.read_text())
repositories = {r['repository'].lower(): r for r in classification['repositories']}
fields = classification['vocabulary']['scientific_field']
reassessment['legacy_domains'] = reassessment['domains']
reassessment['domains'] = {t['label']:dict(sources=0,located=0,lead=0,none_detected=0,unknown=0) for t in fields.values()}
for name in ['Scope not reassessed', 'Insufficient field evidence', 'Field not applicable']:
    reassessment['domains'][name] = dict(sources=0,located=0,lead=0,none_detected=0,unknown=0)
for row in reassessment['rows']:
    repo = repositories.get((row.get('repo') or '').lower())
    labels = [a for a in (repo or {}).get('labels', []) if a['facet']=='scientific_field']
    row['scope_evidence'] = repo
    row['scientific_fields'] = sorted({fields[a['term']]['label'] for a in labels})
    if not row['scientific_fields']:
        row['scientific_fields'] = ['Scope not reassessed' if repo is None or repo.get('acquisition_status')!='acquired' else 'Field not applicable' if repo.get('review_state')=='not_applicable' else 'Insufficient field evidence']
    for name in row['scientific_fields']:
        reassessment['domains'][name]['sources'] += 1
        reassessment['domains'][name][row['result']] += 1
reassessment['field_vocabulary'] = fields
data['source_inventory'] = reassessment
template = (root/'workbench.template.html').read_text()
for filename, site in [('workbench.html','methods'), ('inventory.html','inventory')]:
    site_data = {**data, 'site':site}
    payload = json.dumps(site_data, ensure_ascii=False).replace('<', '\\u003c')
    (root/filename).write_text(template.replace('__PAYLOAD__',payload))
inputs=['authoring-recovery/final-observations.jsonl','consolidate_documents.py','evidence/alabaster-matrix-build.json','evidence/alabaster-matrix-source-link.json','alternative-source-audit/summary.json','explorer.html','workbench.template.html','build_workbench.py','repo-notebook-audit/summary.json','evidence/tool-discovery-provenance.json']
inputs += ['../5-classification-pilot/full-inventory/explorer-data.json', 'reassessment/summary.json', 'reassessment/reconcile.py', 'reassessment/documents.jsonl', 'reassessment/input-sha256.json']
(root/'workbench-sha256.json').write_text(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
print('Built methods-first workbench with full candidate metadata and repository audit')
