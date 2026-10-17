"""Native metering and instruction-schema fixtures with zero live model calls."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import litellm
from litellm.types.utils import Usage
from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.pipelines.recipes.history import pipeline as history
from repo2rlenv.pipelines.recipes.swe_gen import instruction
from repo2rlenv.spec.input import LLMSpec
from repo2rlenv.spec.recipe_options import PRRecipeOptions

root=Path(__file__).resolve().parent
settings=json.loads((root/'glm-generation-adaptation.json').read_text())
model=LLMSpec(provider='openai',model='glm-5.3',endpoint='https://example.invalid/v1',api_key_env='FIXTURE_KEY',max_concurrent=1,timeout_sec=1200,fallback=None)
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    for target,module in [('history',history),('swe_gen',instruction)]:
        output=temp/target;output.mkdir();calls=[]
        native=module.metered_complete
        answer={'analysis':'Synthetic analysis for a mocked transport fixture.', 'instruction':'Synthetic instruction for mocked transport only. '*4} if target=='history' else {'is_substantial':False,'reason':'Synthetic fixture','instruction':None,'tags':['a','b','c']}
        def completion(*args,**kwargs):
            calls.append(kwargs)
            assert kwargs['api_base']=='https://example.invalid/v1' and kwargs['api_key']=='fixture'
            assert kwargs['max_tokens']==131072 and kwargs['timeout']==1200 and kwargs['num_retries']==0
            assert kwargs['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(answer),reasoning_content='fixture'))],usage=Usage(prompt_tokens=5,completion_tokens=8,total_tokens=13))
        ledger=BudgetLedger(output/'budget.sqlite',limit_usd='2')
        with patch.dict(os.environ,{'FIXTURE_KEY':'fixture'}),patch.object(litellm,'completion',new=completion):
            with adapted_authoring(settings,output,metering_target=target):
                if target=='history':
                    response=history.metered_complete(model,ledger=ledger,receipt=output/'model.json',operation_id='fixture',reservation_usd='.75',max_tokens=5000,system='fixture',user='fixture',response_schema=history.HistoricalIssue.model_json_schema())
                    history.HistoricalIssue.model_validate_json(response.content)
                else:
                    result=instruction.write_instruction({'title':'Fixture','body':'Fixture','linked_issue':None,'test_evidence':[],'source_files':['module.py']},PRRecipeOptions(source_paths=["module.py"],test_paths=["tests"]),model,ledger,output/'model.json',operation_id='fixture',resume=False)
                    assert not result.is_substantial
        assert module.metered_complete is native
        assert len(calls)==1
        assert json.loads((output/'model.request.json').read_text())['max_tokens']==131072
        assert json.loads((output/'raw/call-001.json').read_text())['reasoning_content']=='fixture'
print('PASS: native history and SWE-gen metering, approved cap/effort/timeout, zero retries, schema handling, raw capture and context restoration; zero live calls.')
