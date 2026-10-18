"""Admit only a frozen similarity cohort with complete native and cleanup evidence."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from harbor.models.task.task import Task
from prdiff_runtime_input import check_task

ROOT=Path(__file__).resolve().parent


def finalize(cohort,private):
    run='prdiff-'+cohort+'-provider-01';out=ROOT/'evidence'/run
    source=private/(run+'-recovered');native=source/'native/author-output'
    state=json.loads((native/'status.json').read_text());assert state['status']=='passed' and state['model_calls']==0 and len(state['cases'])==6
    checks=json.loads((out/'cleanup-verification.json').read_text());assert len(checks)==6 and all(x['result']=='sandbox_absent' for x in checks)
    records=[json.loads(x) for x in (native/'provider.jsonl').read_text().splitlines()]
    ids={x['sandbox_id'] for x in records if x['stage']=='created'}
    assert len(ids)==6 and ids=={x['worker_name'] for x in checks}
    readiness=[x for x in records if x['stage']=='learner_preflight'];assert len(readiness)==6
    assert all(x['network_block_all'] is True and x['private_paths_and_import_returncode']==0 for x in readiness)
    terminal=[x for x in records if x['stage']=='native_terminal_setup'];assert len(terminal)==6 and all(x['session_started'] and x['model_calls']==0 for x in terminal)
    cohort_root=private/'prdiff-pilot-tasks-02';plan=json.loads((cohort_root/(cohort+'-cohort.json')).read_text());values={}
    for item in plan['tasks']:
        task=cohort_root/item['path'];check_task(task,cohort_root/item['review'])
        cases=[x for x in state['cases'] if x['task']==item['task']]
        assert len(cases)==2 and {x['agent'] for x in cases}=={'nop','oracle'}
        for case in cases:
            result=case['result'];assert result['exception_info'] is None and case['judge_disabled_verified'] is True
            assert result['verifier_environment_mode']=='shared'
            assert result['verifier_result']['rewards']['reward']=={'nop':0,'oracle':1}[case['agent']]
        checksums={x['result']['task_checksum'] for x in cases};assert checksums=={Task(task).checksum};values[item['task']]=checksums.pop()
    for name in ('status.json','provider.jsonl','cleanup.json'):shutil.copyfile(native/name,out/name)
    for name in ('author-evidence-receipt.json','author-process-status.json'):shutil.copyfile(source/name,out/name)
    decision={'stage':'accepted_for_bounded_similarity_pilot','cohort':cohort,'controls_sha256':hashlib.sha256((out/'status.json').read_bytes()).hexdigest(),'task_checksums':values,'accepted_tasks':len(values),
       'profile':'Native deterministic patch-similarity reward; declared offline and tmux tooling adaptations, no model judge.',
       'limitations':['Continuous patch-similarity admission only; no compilation, functional correctness, biological reasoning, pass@1, Atlas admission or training-readiness claim.','Native structural components award credit to reversed changes and some unrelated edits; preserve the reward meaning.','Reference text application and runtime0/1 controls do not establish semantic equivalence of arbitrary alternate fixes.','Image recipe has mutable public base tag and build-time package resolution; no public pinned training image claimed.']}
    (out/'acceptance.json').write_text(json.dumps(decision,indent=2)+'\n')
    archive=private/(run+'-outputs.tar.zst')
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    submission=json.loads((out/'submission.json').read_text())
    summary={'stage':'native_prdiff_provider_controls','status':'passed','selected_tasks':3,'control_trials':6,'native_rewards':[0,1],'model_calls':0,'independently_accepted_similarity_tasks':3,'blind_attempts':0,'solver_pending':3,'exact_owned_sandboxes_absent':6,'checkpoint_commit':submission['checkpoint_commit'],'frozen_input_revision':'0d3df795bc1341c8b2d734f2d988402bb7bc73f9','outer_recovery':{'bytes':archive.stat().st_size,'sha256':digest,'retention_days':7},'interpretation':'Continuous native patch similarity; no functional execution claim.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cohort',choices=['biopython','skbio','bedtools','deseq'],required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(finalize(a.cohort,a.private_root)))
