"""Bounded read-only live diagnostics on the original submitted job handle."""

import argparse
from pathlib import Path

from iris.cli.connect import connect_controller, rpc_client
from iris.rpc import controller_pb2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('biotasks28-') and all(c.isalnum() or c == '-' for c in args.run_id)
    inner = r'''from pathlib import Path
from collections import Counter
import json,os,functools,gzip,importlib.util,hashlib

def tail(path,n=1600):
 with path.open('rb') as f:
  f.seek(max(0,path.stat().st_size-n));return f.read(n).decode(errors='replace')

parts=[];events=[]
for name in ['native-window.json','fresh-controls.json','exported-tasks.json']:
 p=Path('/work/evidence')/name
 if p.exists():parts.append(name+' '+tail(p,2200))
p=Path('/work/native-observations/billing.json')
if p.exists():parts.append('billing '+tail(p))
p=Path('/work/native-observations/native-candidates.json')
if p.exists():
 assert p.stat().st_size <= 10*1024**2
 try:parts.append('native_discovery '+json.dumps({'candidates_returned':len(json.loads(p.read_text()))}))
 except json.JSONDecodeError:parts.append('native_discovery write_in_progress')
for p in Path('/work/evidence').glob('*.log'):parts.append(p.name+' '+tail(p))
p=Path('/work/native-observations/events.jsonl')
if p.exists():
 assert p.stat().st_size <= 10*1024**2
 events=[];incomplete=0
 for line in p.read_text().splitlines():
  try:events.append(json.loads(line))
  except json.JSONDecodeError:incomplete+=1
 parts.append('native_progress '+json.dumps({'events':dict(Counter(e['event'] for e in events)),
  'decisions':dict(Counter(e['outcome']+':'+e.get('reason','') for e in events if e['event']=='native_decision')),
  'incomplete_event_lines':incomplete,'live_observation_only':True}))
 parts.append('events '+tail(p,1800))
for p in sorted(Path('/work/native-observations').glob('validation-*.json.gz'))[-1:]:
 with gzip.open(p,'rt') as f:raw=f.read(16*1024**2+1)
 assert len(raw)<=16*1024**2
 v=json.loads(raw)
 pr=int(p.name.rsplit('-pr-',1)[1].split('.')[0])
 pytest_mode=any('pytest' in cmd for e in events if e['event']=='validation_start' and e.get('pr')==pr
  for cmd in e.get('test_cmds',[]))
 parsers={};parser_sources={}
 source_specs=[('native','log_parsers/pytest_parser.py'),('export','pipelines/_pr_runtime_verifier.py')] if pytest_mode else []
 for name,relative in source_specs:
  source=Path('/work/upstream/src/repo2rlenv')/relative
  spec=importlib.util.spec_from_file_location('original_'+name+'_parser',source)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  parsers[name]=module;parser_sources[name]=hashlib.sha256(source.read_bytes()).hexdigest()
 census={}
 for k in ['pre_log','post_log'] if pytest_mode else []:
  text=v.get(k,'')
  native=parsers['native'].parse_pytest(text)
  exported=parsers['export'].parse_logs('pytest',text)
  census[k]={'native_original_statuses':dict(Counter(native.values())),
   'export_verifier_original_statuses':dict(Counter(exported.values()))}
 parts.append('last_native_validation '+json.dumps({'file':p.name,'status':v['status'],'reason':v.get('reason'),
  'original_parser_sources':parser_sources,'pytest_only_census':pytest_mode,'read_only_status_census_no_regrading':census,
  'logs':{k:{'characters':len(v.get(k,'')),'has_start_marker':'R2E_START_TEST_OUTPUT' in v.get(k,''),
   'ansi_sequences':v.get(k,'').count('\x1b['),'prefix':v.get(k,'')[:400],'suffix':v.get(k,'')[-400:]}
   for k in ['pre_log','post_log']}}))
text='\n'.join(parts)
for k in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN']:
 value=os.environ.get(k)
 if value:text=text.replace(value,'[REDACTED]')
print(text)
'''
    outer = '''import os,subprocess
from pathlib import Path
p=Path(os.environ['IRIS_OUTPUT_DIR'])/'installation.log'
if p.exists():
 with p.open('rb') as f:
  f.seek(max(0,p.stat().st_size-500));print('INSTALL_TAIL',f.read(500).decode(errors='replace'))
p=Path('/opt/biotasks28-tools/docker')
if p.exists():
 r=subprocess.run([str(p),'exec',%r,'python','-c',%r],capture_output=True,text=True,timeout=20)
 print(r.stdout);print(r.stderr)
''' % (args.run_id + '-controller', inner)
    with connect_controller(config_file=args.config) as endpoint:
        with rpc_client(endpoint.url, endpoint.credentials, timeout_ms=45000) as client:
            result = client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(
                task_id='/exedev/' + args.run_id + '/0',
                command=['bash', '-c', 'exec "$IRIS_PYTHON" -c "$1"', '_', outer], timeout_seconds=30))
            print(result.stdout)
            print(result.stderr)
            print('inspection exit', result.exit_code, 'error', result.error)


if __name__ == '__main__':
    main()
