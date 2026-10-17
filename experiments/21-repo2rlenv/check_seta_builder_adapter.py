import sys,runpy,json,tempfile,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
runpy.run_path(str(root/'check_seta_design_replay.py'),run_name='__main__')
import build_seta_designs
from glm_authoring_adapter import adapted_authoring
from repo2rlenv.pipelines.recipes.terminal import runner
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.spec.input import LLMSpec
from litellm.types.utils import Usage
import litellm
settings=json.loads((root/'glm-generation-adaptation.json').read_text());calls=[]
def transport(*a,**k):
 calls.append(k)
 assert k['max_tokens']==131072 and k['timeout']==1200
 assert k['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
 return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',reasoning_content='fixture'))],usage=Usage(prompt_tokens=1,completion_tokens=1,total_tokens=2))
os.environ['OFFLINE_SETA_KEY']='fixture'
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);m=LLMSpec(provider='openai',model='glm-5.3',endpoint='https://example.invalid/v1',api_key_env='OFFLINE_SETA_KEY',timeout_sec=1200,fallback=None)
 with patch.object(litellm,'completion',new=transport),adapted_authoring(settings,p,metering_target='terminal_builder'):
  r=runner.metered_complete(m,ledger=BudgetLedger(p/'ledger.sqlite',limit_usd='5'),receipt=p/'request.json',operation_id='offline',reservation_usd='1.25',max_tokens=10000,resume=False,system='fixture',user='fixture')
 assert r.content=='{}' and len(calls)==1 and (p/'raw/call-001.json').exists()
print('PASS: native builder metering target receives approved GLM settings and preserves raw response; zero live model calls')
