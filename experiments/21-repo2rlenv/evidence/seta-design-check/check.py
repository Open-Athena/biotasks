import json,os,sys,tempfile,tarfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path('experiments/21-repo2rlenv').resolve();sys.path.insert(0,str(root))
import litellm
from litellm.types.utils import Usage
from author_seta_designs import main
calls=[]
def transport(*args,**kwargs):
 calls.append(kwargs)
 assert kwargs['max_tokens']==131072 and kwargs['timeout']==1200 and kwargs['num_retries']==0
 assert kwargs['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
 answer='not-json' if len(calls)==1 else json.dumps({'core_capabilities':['synthetic interval processing'],'draft_spec':'A synthetic offline interval-processing task with explicitly defined coordinate conventions and deterministic artifact checks. '*3})
 return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=answer,reasoning_content='fixture reasoning'))],usage=Usage(prompt_tokens=10,completion_tokens=20,total_tokens=30))
with tempfile.TemporaryDirectory() as temp:
 temp=Path(temp);output=temp/'author-output'
 argv=['author_seta_designs.py','--seeds',str(root/'seeds/seta-genomic-intervals/seeds.json'),'--manifest',str(root/'seeds/seta-genomic-intervals/manifest.json'),'--adaptation',str(root/'glm-generation-adaptation.json'),'--output',str(output)]
 with patch.dict(os.environ,{'REPO2RLENV_MODEL_WORKER':'1','IRIS_OUTPUT_DIR':str(temp/'capture'),'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1','BIOTASKS21_GLM_KEY':'offline-fixture'}),patch.object(sys,'argv',argv),patch.object(litellm,'completion',transport):main()
 records=json.loads((output/'designs.json').read_text())['records']
 assert len(calls)==3 and [r['status'] for r in records]==['failed','designed','designed']
 assert len(list((output/'raw').glob('*.json')))==3
 with tarfile.open(temp/'capture/author-evidence.tar.gz') as archive:
  assert json.loads(archive.extractfile('author-output/designs.json').read())['records']==records
 result={'stage':'offline_native_seta_design_transport','mocked_requests':3,'statuses':[r['status'] for r in records],'native_schema_rejection_preserved':True,'implicit_retries':0,'approved_wire_settings_verified':True,'partial_and_successful_evidence_archived':True,'model_calls':0,'remote_workers':0,'platform_capture_tested':False}
 out=root/'evidence/seta-design-check';out.mkdir(exist_ok=False);(out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
