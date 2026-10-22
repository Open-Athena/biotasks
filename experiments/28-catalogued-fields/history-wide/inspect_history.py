"""Bounded read-only progress/charge inspection of an existing owned history controller."""

import argparse
import datetime
import json
from pathlib import Path

from iris.cli.connect import connect_controller, rpc_client
from iris.rpc import controller_pb2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('biotasks28-history-') and all(c.isalnum() or c == '-' for c in args.run_id)
    inner = r'''import collections,json,os
from pathlib import Path
from decimal import Decimal
out={'observation_only':True,'batches':[],'bootstrap':[]}
p=Path('/work/evidence/history-batches.json')
if p.exists():
 d=json.loads(p.read_text());out['history']={k:d[k] for k in ['repo','state','input_id_count','actual_cost_usd','cost_complete']}
 out['history']['backlog_count_at_last_checkpoint']=len(d['backlog_pr_numbers'])
 out['history']['batch_states']=[{'index':r['index'],'state':r['state'],'selected':len(r['selected_pr_numbers'])} for r in d['batches']]
for path in sorted(Path('/work/native-observations').glob('batch-*')):
 p=path/'events.jsonl';events=[];incomplete=0
 if p.exists():
  assert p.stat().st_size<16*1024**2
  for line in p.read_text().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:incomplete+=1
 sent={e['call'] for e in events if e['event']=='model_request'}
 charged={e['call']:Decimal(e['actual_cost_usd']) for e in events if e['event']=='model_charge' and e['actual_cost_usd'] is not None}
 out['batches'].append({'name':path.name,'events':dict(collections.Counter(e['event'] for e in events)),
  'decisions':dict(collections.Counter(e['outcome']+':'+e.get('reason','') for e in events if e['event']=='native_decision')),
  'dispatched_model_calls':len(sent),'recorded_actual_usd':str(sum(charged.values(),Decimal('0'))),
  'unresolved_at_observation':sorted(sent-set(charged)),'incomplete_event_lines':incomplete,
  'last_event':{k:events[-1][k] for k in ['event','time','call','pr','validation','status'] if k in events[-1]} if events else None})
for p in Path('/work/bootstrap').glob('*/*/bootstrap.json'):
 assert p.stat().st_size<1024**2
 d=json.loads(p.read_text());out['bootstrap'].append({k:d.get(k) for k in ['repo','ref','language','smoke_passed','verify_passed','iterations','test_cmds']})
text=json.dumps(out)
for name in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN']:
 value=os.environ.get(name)
 if value:text=text.replace(value,'[REDACTED]')
print(text)
'''
    outer = """import subprocess
result=subprocess.run(['/opt/biotasks28-tools/docker','exec',%r,'python','-c',%r],capture_output=True,text=True,timeout=20)
print(result.stdout)
if result.returncode:raise RuntimeError('Owned controller unavailable; inspect original handle state')
""" % (args.run_id + '-controller', inner)
    with connect_controller(config_file=args.config) as endpoint:
        with rpc_client(endpoint.url, endpoint.credentials, timeout_ms=45000) as client:
            response = client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(
                task_id='/exedev/' + args.run_id + '/0',
                command=['bash', '-c', 'exec "$IRIS_PYTHON" -c "$1"', '_', outer], timeout_seconds=30))
    assert response.exit_code == 0 and not response.error, (response.exit_code, response.error)
    report = json.loads(response.stdout)
    report.update(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id=args.run_id,
        read_only=True, scope='Live snapshot of original batch/event/billing/bootstrap metadata only. Not terminal reconciliation, native validation, independent grading or a retry.')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
