"""Read only process/cgroup state in containers carrying this run's exact label."""

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
    assert args.run_id.startswith('biotasks28-') and all(c.isalnum() or c == '-' for c in args.run_id)
    inner = r'''import json,os,time
from pathlib import Path
uptime=float(Path('/proc/uptime').read_text().split()[0]);ticks=os.sysconf('SC_CLK_TCK')
rows=[]
for entry in Path('/proc').iterdir():
 if not entry.name.isdecimal():continue
 try:
  argv=(entry/'cmdline').read_bytes().split(b'\0')
  module_index=argv.index(b'-m') if b'-m' in argv else -1
  is_pytest=(module_index>=0 and argv[module_index+1:module_index+2]==[b'pytest']) or (argv and Path(os.fsdecode(argv[0])).name=='pytest')
  if not is_pytest:continue
  stat=(entry/'stat').read_text().rsplit(')',1)[1].split();parent=Path('/proc')/stat[1]
  rows.append({'pid':int(entry.name),'ppid':int(stat[1]),'state':stat[0],
   'age_seconds':round(uptime-int(stat[19])/ticks,3),
   'parent_name':(parent/'comm').read_text().strip() if parent.exists() else None})
 except (OSError,ValueError,IndexError):continue
limits={}
for name in ['cpu.max','memory.max','cpuset.cpus.effective']:
 p=Path('/sys/fs/cgroup')/name
 if p.exists():limits[name]=p.read_text().strip()
print(json.dumps({'observed_epoch':time.time(),'pytest_processes':rows,'cgroup_limits':limits,
 'scope':'Exact-label owned container; process metadata only, no command bodies/environment values or mutations.'}))
'''
    outer = '''import subprocess,json
docker='/opt/biotasks28-tools/docker'
ids=subprocess.run([docker,'ps','-q','--filter',%r],capture_output=True,text=True,check=True,timeout=10).stdout.split()
assert len(ids)<=2
rows=[]
for container in ids:
 r=subprocess.run([docker,'exec',container,'python','-c',%r],capture_output=True,text=True,timeout=15)
 rows.append({'container_id':container,'exit_code':r.returncode,'data':json.loads(r.stdout) if r.returncode==0 else None})
print(json.dumps({'run_id':%r,'owned_containers':rows}))
''' % ('label=biotasks.run=' + args.run_id, inner, args.run_id)
    with connect_controller(config_file=args.config) as endpoint:
        with rpc_client(endpoint.url, endpoint.credentials, timeout_ms=45000) as client:
            result = client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(
                task_id='/exedev/' + args.run_id + '/0',
                command=['bash', '-c', 'exec "$IRIS_PYTHON" -c "$1"', '_', outer], timeout_seconds=40))
    assert result.exit_code == 0 and not result.error, (result.exit_code, result.error)
    report = json.loads(result.stdout)
    report['checked_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report['read_only'] = True
    report['limitations'] = 'A snapshot only. Parent names/ages distinguish candidate main processes but do not alone establish why a process persisted or prove OOM. No process was signalled.'
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
