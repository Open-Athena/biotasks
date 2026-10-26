import json
from pathlib import Path
from biotasks.generation import generation_bridge, resources
root=Path(__file__).resolve().parent
plan=json.loads((root/'inputs-private/run-001/nibabel/plan.json').read_text())
value=generation_bridge.call(plan['backend'],{'action':'preflight','group':plan['group'],'payload_sha256':plan['group']['payload_sha256']},root/'inputs-private/preflight.log')
(root/'preflight-result.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k!='payload_sha256'},indent=2))
