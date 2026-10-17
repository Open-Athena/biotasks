"""Offline native design/transport and evidence-preservation regression checks."""
import json
import os
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import litellm
from litellm.types.utils import Usage
from author_parent_evolution import run

root=Path(__file__).resolve().parent
calls=[]
def completion(*args,**kwargs):
    calls.append(kwargs)
    assert kwargs['max_tokens']==131072 and kwargs['timeout']==1200
    assert kwargs['num_retries']==0
    assert kwargs['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
    answer='invalid json' if len(calls)==1 else json.dumps({'core_capabilities':['numerical stability'],
        'draft_spec':'Synthetic offline test of a numerical-stability design. '*4,
        'filtered_reason':'Synthetic rejection' if len(calls)==3 else None})
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=answer,reasoning_content='fixture'))],usage=Usage(prompt_tokens=10,completion_tokens=20,total_tokens=30))
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    args=SimpleNamespace(parent=root/'seeds/pr2633-parent-v1/parent',manifest=root/'seeds/pr2633-parent-v1/manifest.json',
                         adaptation=root/'glm-generation-adaptation.json',output=temp/'author-output')
    with patch.dict(os.environ,{'REPO2RLENV_MODEL_WORKER':'1','IRIS_OUTPUT_DIR':str(temp/'capture'),
                               'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1','BIOTASKS21_GLM_KEY':'fixture'}),patch.object(litellm,'completion',new=completion):
        run(args)
    state=json.loads((args.output/'designs.json').read_text())
    assert [r['status'] for r in state['records']]==['failed','designed','filtered']
    assert len(calls)==3 and state['built_tasks']==state['independently_accepted_tasks']==0
    assert len(list((args.output/'raw').glob('*.json')))==3
    with tarfile.open(temp/'capture/author-evidence.tar.gz') as archive:
        assert json.loads(archive.extractfile('author-output/designs.json').read())==state
print('PASS: native parent identities and design schema, approved GLM transport, rejected/filtered outcomes and raw archive preservation; zero live calls.')
