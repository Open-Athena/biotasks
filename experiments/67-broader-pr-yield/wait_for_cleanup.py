"""Wait for the exact worker, then finish already-reserved owner cleanup only."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time

from biotasks.validation import budget, controller
from biotasks.validation.files import ValidationError,read_json,require,write_json

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');args=parser.parse_args()
val=root/'inputs-private/run-002/nibabel-handoff/validation'
plan=controller.verify_plan(val)
group=next(g for g in plan['tasks'] if g['task']['task']=='nipy__nibabel-1291')
pipeline=controller.Pipeline(val,plan,group)
directory=pipeline.directory
journal=read_json(directory/'journal.json')
require([s['stage'] for s in journal['stages']][:5]==['candidate_verified','submission_recorded','remote_terminal','archive_readback_verified','publication_resolved'],'Original tests/readback must already be finished')
rb=read_json(directory/'readback.json')
require(rb['durable_readback_verified'] and rb['verified_stopped'],'Original evidence must be retained and execution stopped')
failed=directory/'cleanup/submit.log'
backup=root/'inputs-private/cleanup-submit-first-failure.log'
if failed.exists() and not backup.exists():backup.write_bytes(failed.read_bytes())

def report(state,**values):
    result={'observed_utc':datetime.now(timezone.utc).isoformat(),'state':state,'task':'nipy__nibabel-1291','original_control_run_id':group['run_id'],'test_or_model_retry':False,**values}
    write_json(root/'cleanup-wait-state.json',result)
    print(json.dumps(result),flush=True)

while True:
    journal=read_json(directory/'journal.json')
    stages=[s['stage'] for s in journal['stages']]
    if stages[-1]=='cleanup_verified':
        proof=read_json(directory/'cleanup-proof.json');require(proof['verified_empty'],'Owner cleanup must be empty')
        report('cleanup_verified',cleanup_run_id=group['run_id']+'-cleanup');break
    require(stages[-1] in ['publication_resolved','cleanup_terminal'],'Never repeat or advance primary test execution')
    aux,aux_dir,extra=pipeline.auxiliary('cleanup',archival_verified=True,control_archive_sha256=rb['control_archive_sha256'],protected_base=rb['protected_base'])
    budget.verify_reserved(pipeline.ledger,aux['run_id']) if not (aux_dir/'accounting.json').exists() else None
    if not (aux_dir/'submission.json').exists():
        try:
            preflight=pipeline.client('preflight',aux,aux_dir,**extra)
            require(preflight['worker_id']==extra['target']['worker_id'],'Never move owner cleanup to another worker')
        except ValidationError:
            log=aux_dir/'preflight.log'
            if not log.exists() or 'No compatible existing reserved worker with declared headroom' not in log.read_text():raise
            report('waiting_for_original_worker_headroom',cleanup_run_id=aux['run_id'])
            if not args.watch:break
            time.sleep(300);continue
    # All effects below are the unchanged frozen cleanup lifecycle, retaining
    # its exact job identity, resource checks, RPC lock and no-retry policy.
    pipeline.step()
    if args.watch:time.sleep(300)
    else:break
