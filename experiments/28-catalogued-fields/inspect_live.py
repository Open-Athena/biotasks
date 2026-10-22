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
import json,os,functools

def tail(path,n=1600):
 with path.open('rb') as f:
  f.seek(max(0,path.stat().st_size-n));return f.read(n).decode(errors='replace')

parts=[]
for name in ['native-window.json','fresh-controls.json','exported-tasks.json']:
 p=Path('/work/evidence')/name
 if p.exists():parts.append(name+' '+tail(p,2200))
p=Path('/work/native-observations/billing.json')
if p.exists():parts.append('billing '+tail(p))
for p in Path('/work/evidence').glob('*.log'):parts.append(p.name+' '+tail(p))
p=Path('/work/native-observations/events.jsonl')
if p.exists():parts.append('events '+tail(p,1800))
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
