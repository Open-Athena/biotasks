"""Native no-op/reference checks for a fixed three-task similarity cohort."""
import argparse
import asyncio
import json
import os
import time
from importlib.metadata import version
from pathlib import Path
from harbor.models.task.task import Task
from harbor.models.task.verifier_mode import resolve_task_verifier_mode
from harbor.trial.trial import Trial
from prdiff_runtime_input import check_task
from run_pr_provider_preflight import cleanup,config
from preserve_author_output import preserve


async def run(cohort_path,output):
    assert os.environ.get('REPO2RLENV_MODEL_WORKER')=='1' and version('harbor')=='0.22.0'
    cohort=json.loads(cohort_path.read_text());assert cohort['selected_count']==len(cohort['tasks'])==3
    output.mkdir(exist_ok=False);state={'stage':'native_prdiff_provider_controls','cohort':cohort['cohort'],'status':'running','model_calls':0,'cases':[]}
    os.environ['BIOTASKS21_PROVIDER_MODULE']='prdiff_provider_environment';os.environ['BIOTASKS21_PROVIDER_RECEIPTS']=str((output/'provider.jsonl').resolve())
    deadline=time.monotonic()+int(os.environ['BIOTASKS21_PREFLIGHT_REMAINING_SEC'])
    try:
        for item in cohort['tasks']:
            task=Path(item['path']);review=check_task(task,Path(item['review']))
            assert resolve_task_verifier_mode(Task(task).config).value=='shared'
            os.environ['BIOTASKS21_PRDIFF_BASE']=review['base'];os.environ['BIOTASKS21_RUNTIME_MANIFEST']=str(Path(item['runtime']).resolve())
            for agent,expected in [('nop',0),('oracle',1)]:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Provider cohort deadline reached')
                spec=config(task,output,agent);spec.trial_name=item['task']+'-'+agent
                trial=await Trial.create(spec);result=await asyncio.wait_for(trial.run(),timeout=min(900,remaining))
                record={'task':item['task'],'agent':agent,'expected_reward':expected,'result':result.model_dump(mode='json')};state['cases'].append(record)
                (output/'status.json').write_text(json.dumps(state,indent=2)+'\n')
                assert result.exception_info is None and result.verifier_result.rewards['reward']==expected
                assert result.verifier_environment_mode.value=='shared'
                sidecar=output/'trials'/spec.trial_name/'verifier/reward-details.json'
                details=json.loads(sidecar.read_text());assert details['components']['llm_judge'] is None and details['judge_model'] is None and details['judge_endpoint'] is None
                record['judge_disabled_verified']=True;cleanup(output)
        for item in cohort['tasks']:
            cases=[x for x in state['cases'] if x['task']==item['task']];assert len(cases)==2
            assert cases[0]['result']['task_checksum']==cases[1]['result']['task_checksum']
        state['status']='passed'
    except BaseException as exc:
        state.update(status='failed',error_type=type(exc).__name__);raise
    finally:
        try:cleanup(output)
        finally:
            (output/'status.json').write_text(json.dumps(state,indent=2)+'\n');preserve(output,Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cohort',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();asyncio.run(run(a.cohort,a.output))
