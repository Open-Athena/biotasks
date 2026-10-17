"""Verify all three native terminal authoring paths share the approved adaptation."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import litellm
from litellm.types.utils import Usage
from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns import structured
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.pipelines.recipes.terminal import templates, runner
from repo2rlenv.spec.input import LLMSpec

root=Path(__file__).resolve().parent
settings=json.loads((root/'glm-generation-adaptation.json').read_text())
model=LLMSpec(provider='openai',model='glm-5.3',endpoint='https://example.invalid/v1',api_key_env='FIXTURE_KEY',max_concurrent=1,timeout_sec=1200,fallback=None)
with tempfile.TemporaryDirectory() as temp:
    output=Path(temp);calls=[]
    originals=[m.metered_complete for m in (templates,structured,runner)]
    programs='\n\n'.join('def test_case_'+str(i)+'():\n    assert True' for i in range(5))
    responses=[{'description':'Synthetic mocked template description. '*4,'truth':'Synthetic mocked template truth. '*4}, {'code':programs},{'code':programs},{'fixture':True}]
    def completion(*args,**kwargs):
        assert kwargs['api_base']=='https://example.invalid/v1' and kwargs['api_key']=='fixture'
        assert kwargs['max_tokens']==131072 and kwargs['timeout']==1200 and kwargs['num_retries']==0
        assert kwargs['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
        answer=responses[len(calls)];calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(answer),reasoning_content='fixture'))],usage=Usage(prompt_tokens=5,completion_tokens=8,total_tokens=13))
    ledger=BudgetLedger(output/'budget.sqlite',limit_usd='5')
    with patch.dict(os.environ,{'FIXTURE_KEY':'fixture'}),patch.object(litellm,'completion',new=completion):
        with adapted_authoring(settings,output,metering_target='terminal_stages'):
            design=templates.design({'title':'fixture'},template_prompt='fixture',initial_prompt='fixture',final_prompt='fixture',capabilities=['fixture'],model=model,ledger=ledger,receipt=output/'template.json',operation_id='template',resume=False)
            assert design.initial_tests==design.final_tests==programs
            runner.metered_complete(model,ledger=ledger,receipt=output/'builder.json',operation_id='builder',reservation_usd='.75',max_tokens=7000,system='fixture',user='fixture')
    assert [m.metered_complete for m in (templates,structured,runner)]==originals
    assert len(calls)==4
    raw=sorted((output/'raw').glob('call-*.json'))
    assert len(raw)==4 and all(json.loads(p.read_text())['requested_max_tokens']==131072 for p in raw)
print('PASS: native template, initial/final structured tests and builder meter; four distinct raw records; settings and restoration; zero live calls.')
