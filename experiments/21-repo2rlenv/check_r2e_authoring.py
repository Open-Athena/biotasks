"""Offline transport and interrupted-controller recovery checks; no live services."""
import contextlib
import dataclasses
import json
import os
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import litellm
from litellm.types.utils import Usage
from daytona.common.errors import DaytonaNotFoundError
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.campaigns.events import ProgressEvent
from repo2rlenv.spec.input import LLMSpec
from repo2rlenv.pipelines.recipes.r2e import pipeline
import run_r2e_authoring as controller
from glm_authoring_adapter import adapted_authoring

ROOT = Path(__file__).resolve().parent
settings = json.loads((ROOT / 'glm-generation-adaptation.json').read_text())
os.environ.update(REPO2RLENV_MODEL_WORKER='1', BIOTASKS21_GLM_ENDPOINT='https://example.invalid/v1', OFFLINE_R2E_KEY='fixture')
calls=[]
def transport(*a, **k):
    calls.append(k)
    assert k['max_tokens']==131072 and k['timeout']==1200
    assert k['extra_body']['chat_template_kwargs']['reasoning_effort']=='medium'
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='{}',reasoning_content='fixture'))],usage=Usage(prompt_tokens=1,completion_tokens=1,total_tokens=2))

@dataclasses.dataclass
class Result:
    out_dir: Path
    emitted: int = 0

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    model=LLMSpec(provider='openai',model='glm-5.3',endpoint='https://example.invalid/v1',api_key_env='OFFLINE_R2E_KEY',timeout_sec=1200,fallback=None)
    with patch.object(litellm,'completion',new=transport),adapted_authoring(settings,root,metering_target='r2e'):
        pipeline.metered_complete(model,ledger=BudgetLedger(root/'meter.sqlite',limit_usd='5'),receipt=root/'request.json',operation_id='offline',reservation_usd='0.75',max_tokens=6000,resume=False,system='fixture',user='fixture')
    assert len(calls)==1 and (root/'raw/call-001.json').exists()
    for fail in (False,True):
        directory=root/str(fail);directory.mkdir()
        os.environ['IRIS_OUTPUT_DIR']=str(directory/'capture')
        worker=SimpleNamespace(id='fixture')
        worker.exec=lambda *a,**k:SimpleNamespace(checked=lambda *a:None)
        worker.download=lambda remote,local:local.write_bytes(b'fixture remote evidence')
        def absent(*a):raise DaytonaNotFoundError('fixture absent')
        worker.client=SimpleNamespace(get=absent)
        stopped=[]
        def provision(*a,**k):
            receipt=directory/'worker.json';receipt.write_text('{}');return worker,receipt
        class Pipeline:
            def __init__(self,spec,options):
                assert spec.llm.timeout_sec==1200 and spec.llm.fallback is None
                assert options.target==3 and options.max_candidates==10
            def set_event_callback(self,callback):self.callback=callback
            def run(self,out):
                self.callback(ProgressEvent(recipe='r2e',stage='author',state='started'))
                (out.parent/'partial.json').write_text('{"stage":"author"}')
                if fail:raise RuntimeError('fixture interruption')
                return Result(out)
        args=SimpleNamespace(profile=ROOT/'r2e-skbio-worker.json',adaptation=ROOT/'glm-generation-adaptation.json',wheel=root/'fixture.whl',campaign=directory/'campaign',worker_name='fixture',run_id='fixture')
        with patch.object(controller,'check_runtime_wheel',return_value='fixture'),patch.object(controller,'provision_worker',new=provision),patch.object(controller,'stop_worker',new=lambda *a:stopped.append(True)),patch.object(controller,'R2EPipeline',new=Pipeline),patch.object(controller,'adapted_authoring',new=lambda *a,**k:contextlib.nullcontext()):
            try:controller.run(args)
            except RuntimeError:
                assert fail
            else:assert not fail
        assert stopped==[True]
        status=json.loads((args.campaign/'controller-result.json').read_text())
        assert status['status']==('failed' if fail else 'completed')
        assert status['cleanup']=='confirmed_absent_404'
        with tarfile.open(directory/'capture/r2e-campaign.tar.gz') as archive:
            assert 'campaign/partial.json' in archive.getnames()
            assert 'campaign/remote-evidence.tar.gz' in archive.getnames()
print('PASS: R2E transport settings, native bounds, success/failure capture and cleanup; no live model or worker calls')
