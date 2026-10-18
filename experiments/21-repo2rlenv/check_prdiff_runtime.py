"""Reject changed inputs and exercise control lifecycle without provider/model calls."""
import asyncio
import copy
import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from harbor.models.task.task import Task
from harbor.models.task.verifier_mode import resolve_task_verifier_mode
from harbor.trial.network_policy import resolve_trial_network_plan
from prdiff_runtime_input import check_task
import run_prdiff_provider_controls as controls
from run_pr_provider_preflight import config

ROOT=Path('/tmp/biotasks21-private/prdiff-pilot-tasks-02')
for cohort_name in ('biopython','skbio','bedtools','deseq'):
    cohort=json.loads((ROOT/(cohort_name+'-cohort.json')).read_text())
    for item in cohort['tasks']:
        check_task(ROOT/item['path'],ROOT/item['review'])
        assert resolve_task_verifier_mode(Task(ROOT/item['path']).config).value=='shared'
        spec=config(ROOT/item['path'],ROOT/'unused','nop')
        plan=resolve_trial_network_plan(Task(ROOT/item['path']).config,spec.agent,spec.environment,None,verifier_mode=resolve_task_verifier_mode(Task(ROOT/item['path']).config))
        assert plan.agent_env_baseline.network_mode.value==plan.agent_phase.network_mode.value==plan.verifier_phase.network_mode.value=='no-network'
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);cohort=json.loads((ROOT/'bedtools-cohort.json').read_text());item=cohort['tasks'][0]
    task=root/'task';shutil.copytree(ROOT/item['path'],task)
    review=ROOT/item['review'];docker=task/'environment/Dockerfile';original=docker.read_bytes()
    docker.write_bytes(original+b'changed')
    try:check_task(task,review)
    except ValueError:pass
    else:raise AssertionError('Changed runtime accepted')
    docker.write_bytes(original);extra=task/'unreviewed';extra.write_text('extra')
    try:check_task(task,review)
    except ValueError:pass
    else:raise AssertionError('Additional asset accepted')
    extra.unlink();script=task/'tests/test.sh';mode=script.stat().st_mode & 0o7777;script.chmod(0o600)
    try:check_task(task,review)
    except ValueError:pass
    else:raise AssertionError('Changed executable mode accepted')
    script.chmod(mode);check_task(task,review)
    for item in cohort['tasks']:
        for name in ('path','review','runtime'):item[name]=str(ROOT/item[name])
    path=root/'cohort.json';path.write_text(json.dumps(cohort))
    calls=[];bad_reward=False
    async def create(spec):
        assert spec.agent.name in ('nop','oracle') and spec.environment.override_gpus==0
        assert spec.environment.override_cpus==2 and spec.environment.override_memory_mb==4096
        calls.append(spec.trial_name);value=1 if spec.agent.name=='oracle' else 0
        if bad_reward and spec.agent.name=='oracle':value=0
        checksum=Task(spec.task.path).checksum
        async def run():
            sidecar=spec.trials_dir/spec.trial_name/'verifier/reward-details.json';sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({'components':{'llm_judge':None},'judge_model':None,'judge_endpoint':None}))
            row={'exception_info':None,'verifier_result':{'rewards':{'reward':value}},'task_checksum':checksum}
            return SimpleNamespace(exception_info=None,verifier_result=SimpleNamespace(rewards={'reward':value}),task_checksum=checksum,
                verifier_environment_mode=SimpleNamespace(value='shared'),model_dump=lambda **kw:row)
        return SimpleNamespace(run=run)
    env={'REPO2RLENV_MODEL_WORKER':'1','BIOTASKS21_PREFLIGHT_REMAINING_SEC':'1800','IRIS_OUTPUT_DIR':str(root/'capture')}
    with patch.dict(os.environ,env),patch.object(controls.Trial,'create',new=AsyncMock(side_effect=create)), \
         patch.object(controls,'cleanup') as clean,patch.object(controls,'preserve'):
        asyncio.run(controls.run(path,root/'output'))
        assert len(calls)==6 and clean.call_count==7
        assert json.loads((root/'output/status.json').read_text())['status']=='passed'
        bad_reward=True
        try:asyncio.run(controls.run(path,root/'wrong-reward'))
        except AssertionError:pass
        else:raise AssertionError('Incorrect oracle reward accepted')
        assert json.loads((root/'wrong-reward/status.json').read_text())['status']=='failed'
    with patch.dict(os.environ,{'BIOTASKS21_PROVIDER_MODULE':'prdiff_provider_environment'}):
        assert config(task,root/'unused','nop').environment.import_path=='prdiff_provider_environment:RecordedDaytonaEnvironment'
print('PASS: twelve exact shared-verifier inputs; altered bytes/assets/modes rejected; six-case lifecycle/cleanup; wrong oracle rejected; no services.')
