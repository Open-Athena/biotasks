"""One blind attempt per runtime-accepted native patch-similarity task."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from harbor.models.task.task import Task
from harbor.trial.trial import Trial
from glm_solver_settings import ATTEMPT_TIMEOUT_SEC
from prdiff_runtime_input import check_task
from run_pr_blind_solver import solver_config
from run_pr_provider_preflight import cleanup
from preserve_author_output import preserve


def inputs(cohort_path, controls_path, acceptance_path):
    cohort=json.loads(cohort_path.read_text())
    controls=json.loads(controls_path.read_text())
    acceptance=json.loads(acceptance_path.read_text())
    assert controls['status']=='passed' and controls['model_calls']==0
    assert controls['cohort']==cohort['cohort']==acceptance['cohort']
    assert acceptance['stage']=='accepted_for_bounded_similarity_pilot'
    assert acceptance['controls_sha256']==hashlib.sha256(controls_path.read_bytes()).hexdigest()
    assert len(cohort['tasks'])==cohort['selected_count']==3
    expected={}
    for item in cohort['tasks']:
        task=Path(item['path']);review=check_task(task,Path(item['review']))
        cases=[x for x in controls['cases'] if x['task']==item['task']]
        assert len(cases)==2 and {x['agent'] for x in cases}=={'nop','oracle'}
        checksums=set()
        for case in cases:
            result=case['result'];assert result['exception_info'] is None and case['judge_disabled_verified'] is True
            assert result['verifier_result']['rewards']['reward']=={'nop':0,'oracle':1}[case['agent']]
            checksums.add(result['task_checksum'])
        assert checksums=={Task(task).checksum}=={acceptance['task_checksums'][item['task']]}
        expected[item['task']]={'checksum':checksums.pop(),'review':review}
    assert set(expected)==set(acceptance['task_checksums'])
    return cohort,expected


async def run(args):
    assert os.environ.get('REPO2RLENV_MODEL_WORKER')=='1'
    cohort,expected=inputs(args.cohort,args.controls,args.acceptance)
    endpoint=os.environ['BIOTASKS21_GLM_ENDPOINT'];assert os.environ.get('BIOTASKS21_GLM_KEY')
    os.environ['OPENAI_API_KEY']=os.environ['BIOTASKS21_GLM_KEY']
    os.environ['BIOTASKS21_PROVIDER_MODULE']='prdiff_provider_environment'
    args.output.mkdir(exist_ok=False)
    os.environ['BIOTASKS21_PROVIDER_RECEIPTS']=str((args.output/'provider.jsonl').resolve())
    state={'stage':'blind_native_similarity_solver','cohort':cohort['cohort'],'status':'started','attempt_limit_per_task':1,'attempts':[]}
    try:
        for item in cohort['tasks']:
            frozen=expected[item['task']]
            os.environ['BIOTASKS21_PRDIFF_BASE']=frozen['review']['base']
            os.environ['BIOTASKS21_RUNTIME_MANIFEST']=str(Path(item['runtime']).resolve())
            spec=solver_config(Path(item['path']),args.output,endpoint);spec.trial_name=item['task']+'-blind-01'
            row={'task':item['task'],'status':'started','task_checksum':frozen['checksum']};state['attempts'].append(row)
            (args.output/'solver-status.json').write_text(json.dumps(state,indent=2)+'\n')
            trial=await Trial.create(spec);result=await asyncio.wait_for(trial.run(),timeout=ATTEMPT_TIMEOUT_SEC)
            assert result.task_checksum==frozen['checksum']
            row.update(status='completed' if result.exception_info is None else 'trial_failed',result=result.model_dump(mode='json'))
            if result.exception_info is None:
                details=json.loads((args.output/'trials'/spec.trial_name/'verifier/reward-details.json').read_text())
                assert details['components']['llm_judge'] is None and details['judge_model'] is None and details['judge_endpoint'] is None
                row['judge_disabled_verified']=True
            cleanup(args.output)
            if result.exception_info is not None:raise RuntimeError('Native trial failed; remaining tasks unattempted')
        state['status']='completed'
    except BaseException as exc:
        state.update(status='incomplete',error_type=type(exc).__name__);raise
    finally:
        try:cleanup(args.output)
        finally:
            (args.output/'solver-status.json').write_text(json.dumps(state,indent=2)+'\n')
            preserve(args.output,Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cohort','controls','acceptance','output'):p.add_argument('--'+name,type=Path,required=True)
    asyncio.run(run(p.parse_args()))
