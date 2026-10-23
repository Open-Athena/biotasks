"""Read original live validation refs and export hashes, never payload data or execution."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

from iris.cli.connect import connect_controller, rpc_client
from iris.rpc import controller_pb2


INNER = r'''import gzip,hashlib,json,os,re,tomllib
from pathlib import Path
def sha(raw):return hashlib.sha256(raw).hexdigest()
out={'observation_only':True,'validation_ref_uses':[],'task_contracts':[],'incomplete_event_lines':0}
ledger=Path('/work/evidence/history-batches.json')
if ledger.exists():out['native_state']=json.loads(ledger.read_text())['state']
for batch in sorted(Path('/work/native-observations').glob('batch-*')):
 events=batch/'events.jsonl'
 if not events.exists():continue
 assert events.stat().st_size<16*1024**2
 for line in events.read_text().splitlines():
  try:event=json.loads(line)
  except json.JSONDecodeError:
   out['incomplete_event_lines']+=1;continue
  if event['event']!='validation_start':continue
  matches=list(batch.glob('discovery-pr-'+str(event['pr'])+'.json.gz'))
  assert len(matches)==1 and matches[0].stat().st_size<1024**2
  original=matches[0].read_bytes()
  with gzip.open(matches[0],'rb') as stream:decoded=stream.read(4*1024**2+1)
  assert len(decoded)<=4*1024**2
  descriptor=json.loads(decoded);head=descriptor['headRefOid'];assert re.fullmatch('[0-9a-f]{40}',head)
  out['validation_ref_uses'].append({'batch':batch.name,'event':event,'head_ref':head,
   'descriptor_original_gzip_sha256':sha(original)})
for path in sorted(Path('/work/outputs').glob('*/*/task.toml')):
 assert path.stat().st_size<1024**2
 raw=path.read_bytes();contract=tomllib.loads(raw.decode());meta=contract['metadata']['repo2env']
 test=path.parent/'tests/test.sh';assert test.stat().st_size<1024**2
 text=test.read_text();f2p=json.loads((path.parent/'tests/f2p.json').read_text());p2p=json.loads((path.parent/'tests/p2p.json').read_text())
 out['task_contracts'].append({'task':path.parent.name,'task_toml_sha256':sha(raw),
  'provenance':{k:meta.get(k) for k in ['pipeline','pipeline_version','repo','ref','reference','source_access','synthesis_llm']},
  'agent':contract.get('agent'),'verifier':contract['verifier'],
  'test_script_sha256':sha(text.encode()),'patch_paths':sorted(set(re.findall(r'^diff --git a/.*? b/(.*?)$',text,re.M))),
  'f2p_count':len(f2p),'p2p_count':len(p2p)})
text=json.dumps(out)
assert len(text)<8*1024**2
for name in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN']:
 value=os.environ.get(name)
 if value:text=text.replace(value,'[REDACTED]')
print(text)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert args.run_id.startswith('biotasks28-history-') and all(c.isalnum() or c == '-' for c in args.run_id)
    outer = """import subprocess
result=subprocess.run(['/opt/biotasks28-tools/docker','exec',%r,'python','-c',%r],capture_output=True,text=True,timeout=25)
print(result.stdout)
if result.returncode:raise RuntimeError('Original controller unavailable; inspect same handle, do not retry native work')
""" % (args.run_id + '-controller', INNER)
    with connect_controller(config_file=args.config) as endpoint:
        with rpc_client(endpoint.url, endpoint.credentials, timeout_ms=45000) as client:
            result = client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(
                task_id='/exedev/' + args.run_id + '/0', command=['bash', '-c', 'exec "$IRIS_PYTHON" -c "$1"', '_', outer],
                timeout_seconds=30))
    assert result.exit_code == 0 and not result.error, (result.exit_code, result.error)
    report = json.loads(result.stdout)
    report.update(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id=args.run_id,
        read_only=True, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        independent_acceptance_asserted=False,
        scope='Original live validation-start/head-descriptor hashes and export-contract hashes/settings/path/count metadata only. No raw fixture bytes, model/native/control runs, changes or final coverage/retention claims. Terminal-byte binding still required.')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'checked_utc': report['checked_utc'], 'run_id': args.run_id,
        'native_state': report.get('native_state'), 'validation_starts': len(report['validation_ref_uses']),
        'unique_refs': len({ref for row in report['validation_ref_uses'] for ref in [row['event']['base_commit'], row['head_ref']]}),
        'export_contracts': len(report['task_contracts']), 'incomplete_event_lines': report['incomplete_event_lines'],
        'independent_acceptance_asserted': False}))


if __name__ == '__main__':
    main()
