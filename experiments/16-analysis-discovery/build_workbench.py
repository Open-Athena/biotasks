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
data['source_inventory'] = reassessment
template = (root/'workbench.template.html').read_text()
for filename, site in [('workbench.html','methods'), ('inventory.html','inventory')]:
    site_data = {**data, 'site':site}
    payload = json.dumps(site_data, ensure_ascii=False).replace('<', '\\u003c')
    (root/filename).write_text(template.replace('__PAYLOAD__',payload))
inputs=['authoring-recovery/final-observations.jsonl','consolidate_documents.py','evidence/alabaster-matrix-build.json','evidence/alabaster-matrix-source-link.json','alternative-source-audit/summary.json','explorer.html','workbench.template.html','build_workbench.py','repo-notebook-audit/summary.json','evidence/tool-discovery-provenance.json']
inputs += ['reassessment/summary.json', 'reassessment/reconcile.py', 'reassessment/documents.jsonl', 'reassessment/input-sha256.json']
(root/'workbench-sha256.json').write_text(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
print('Built methods-first workbench with full candidate metadata and repository audit')
