"""Build the methods-first workbench from the normalized explorer data."""
from pathlib import Path
import json
root = Path(__file__).resolve().parent
source = (root/'explorer.html').read_text()
payload = source.split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0]
data = json.loads(payload)
data['tool_provenance'] = json.loads((root/'evidence/tool-discovery-provenance.json').read_text())
data['repository_audit'] = json.loads((root/'repo-notebook-audit/summary.json').read_text())
payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
(root/'workbench.html').write_text((root/'workbench.template.html').read_text().replace('__PAYLOAD__',payload))
print('Built methods-first workbench with full candidate metadata')
