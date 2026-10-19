import asyncio,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
os.environ['LITELLM_LOCAL_MODEL_COST_MAP']='True'
import httpx
from openai import AsyncOpenAI
from litellm import acompletion
b=Path('/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv');c=b/'continuation-20261018';sys.path[:0]=[str(c),str(b)]
from native_solver_transport import solver_transport_kwargs
from glm_solver_settings import MAX_OUTPUT_TOKENS,MAX_TURNS,ATTEMPT_TIMEOUT_SEC
fixture_token='transport-fixture-token-'*3;options=solver_transport_kwargs('https://fixture.invalid/v1',fixture_token);assert options['max_turns']==MAX_TURNS==12 and options['llm_call_kwargs']['max_tokens']==MAX_OUTPUT_TOKENS==2048 and ATTEMPT_TIMEOUT_SEC==900
requests=[]
def handle(request):
 body=json.loads(request.content);assert request.url.host=='fixture.invalid';assert request.headers['X-Biotasks21-Inference-Token']==fixture_token;assert body['model']=='glm-5.3' and body['max_tokens']==2048;assert not any(key in body for key in ['extra_headers','reasoning_effort','thinking','chat_template_kwargs']);assert fixture_token.encode() not in request.content;requests.append(body)
 return httpx.Response(200,json={'id':'synthetic-completion','object':'chat.completion','created':0,'model':'glm-5.3','choices':[{'index':0,'message':{'role':'assistant','content':'fixture response'},'finish_reason':'stop'}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
async def main():
 async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
  async with AsyncOpenAI(api_key='fixture-not-a-secret',base_url=options['api_base'],http_client=http) as client:
   result=await acompletion(model='openai/glm-5.3',messages=[{'role':'user','content':'synthetic transport fixture'}],api_key='fixture-not-a-secret',api_base=options['api_base'],client=client,**options['llm_call_kwargs']);assert result.choices[0].message.content=='fixture response'
asyncio.run(main());assert len(requests)==1
record={'stage':'pinned_native_LiteLLM_OpenAI_HTTP_options_fixture_passed','model_calls':0,'network_requests':0,'synthetic_mocked_requests':1,'harbor_version':importlib.metadata.version('harbor'),'litellm_version':importlib.metadata.version('litellm'),'openai_version':importlib.metadata.version('openai'),'application_header_present_on_HTTP_request':True,'application_token_absent_from_model_payload':True,'API_model_name':'glm-5.3','max_output_tokens':2048,'agent_turns':12,'attempt_timeout_seconds':900,'effort_and_thinking_fields_unset':True};(c/'native-solver-HTTP-header-check.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
