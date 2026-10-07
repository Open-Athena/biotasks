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
payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
(root/'workbench.html').write_text((root/'workbench.template.html').read_text().replace('__PAYLOAD__',payload))
inputs=['alternative-source-audit/summary.json','explorer.html','workbench.template.html','build_workbench.py','repo-notebook-audit/summary.json','evidence/tool-discovery-provenance.json']
(root/'workbench-sha256.json').write_text(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
print('Built methods-first workbench with full candidate metadata and repository audit')
