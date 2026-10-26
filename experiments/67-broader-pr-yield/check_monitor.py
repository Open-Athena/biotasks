"""Offline monitor contract checks, with no API or native execution."""
import importlib.util
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('monitor_under_test', root/'monitor.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
scratch = root/'inputs-private/monitor-contract-check'; assert not scratch.exists(); scratch.mkdir()
module.ROOT = scratch; module.WORK = scratch/'work'; module.alive = lambda: True

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj))

try:
    # A killed second batch leaves an old backlog even though its durable
    # entry log contains work beyond the first completed batch.
    observations = scratch / 'partial-observations'; observations.mkdir()
    history = {'batches':[{'entered':[1], 'finished':1}, {'started':2}], 'backlog_pr_numbers':[2,3,4]}
    unknown = module.history_coverage(history, observations)
    assert unknown['entered'] is None and unknown['backlog'] is None
    (observations/'events.jsonl').write_text(''.join(json.dumps({'event':'candidate_entered','pr':n})+'\n' for n in [1,2,3]))
    coverage = module.history_coverage(history, observations)
    assert coverage['entered']==3 and coverage['backlog']==1 and coverage['unfinished_native_batch']
    closed = {'batches':[{'entered':[1,2,3],'finished':3}], 'backlog_pr_numbers':[4]}
    assert module.history_coverage(closed, observations)['entered']==3
    budget={'events':[], 'recorded_paid_cost_usd':2.196603, 'additional_allocated_cpu_hours':14.89, 'outstanding_cpu_hour_reservations':6.33, 'outstanding_reservations_usd':23.07}
    write(scratch/'budget.json', budget); write(scratch/'candidates.json', {'candidates':[{},{}]})
    write(scratch/'manifest.json', {'budget_ledger':str(scratch/'budget.json'), 'cases':[{'id':'nibabel','run_id':'test','candidates':{'path':str(scratch/'candidates.json')}}]})
    value=module.snapshot(); c=value['cases'][0]
    assert value['state']=='monitoring' and c['phase']=='not_started' and c['exports'] is None
    assert 'pending' in module.render(value) and c['model_cost_usd'] is None
    gen=module.WORK/'nibabel/runs/generation'
    write(gen/'journal.json', {'stages':[{'stage':s} for s in module.STAGES]})
    write(gen/'readback.json', {'durable_readback_verified':True,'exported_tasks':['test-one']})
    write(gen/'cleanup-proof.json', {'verified_empty':True})
    value=module.snapshot(); assert value['cases'][0]['phase']=='export_ready' and value['cases'][0]['exports']==1
    val=module.WORK/'nibabel-handoff/validation'; write(val/'plan.json', {'tasks':[{'id':'test-task'}]})
    directory=val/'runs/test-task'
    write(directory/'readback.json', {'positive_control_pair':True,'clean_oracle_command':True,'complete_parseable_pair':True,'all_p2p_pass_both':True})
    # A readback alone must not count an uncleaned pair.
    value=module.snapshot(); assert value['cases'][0]['positive']==value['cases'][0]['clean']==0
    write(directory/'journal.json', {'stages':[{'stage':s} for s in module.STAGES]}); write(directory/'cleanup-proof.json', {'verified_empty':True})
    value=module.snapshot(); assert value['cases'][0]['positive']==value['cases'][0]['clean']==1
    write(directory/'readback.json', {'positive_control_pair':True,'clean_oracle_command':False,'complete_parseable_pair':True,'all_p2p_pass_both':True})
    value=module.snapshot(); assert value['cases'][0]['positive']==1 and value['cases'][0]['clean']==0
    module.alive=lambda:False; assert module.snapshot()['state']=='workflow_complete'
    write(directory/'journal.json', {'stages':[]}); assert module.snapshot()['state']=='controller_stopped_requires_review'
    assert module.signature(value)==module.signature({**value,'observed_utc':'later'})
    print('Monitor contract checks passed: interrupted-batch coverage, unknowns, cleanup gate, strict clean flags, terminal/hold, stable signature')
finally:
    shutil.rmtree(scratch)
