"""Snapshot only process names/ages and cgroups in this run's owned containers."""

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
    outer = r'''import collections,json,subprocess,time
docker='/opt/biotasks28-tools/docker'
def read(argv):
 r=subprocess.run([docker,*argv],capture_output=True,text=True,timeout=10)
 assert len(r.stdout)<1024**2 and len(r.stderr)<1024**2
 return r
ids=read(['ps','-q','--filter','label=biotasks.run='+RUN_ID]).stdout.split()
assert len(ids)<=2
rows=[]
for container in ids:
 top=read(['top',container,'-eo','pid,ppid,stat,etimes,comm'])
 processes=[]
 if top.returncode==0:
  for line in top.stdout.splitlines()[1:]:
   pid,ppid,state,age,name=line.split(None,4)
   processes.append({'host_pid':int(pid),'host_ppid':int(ppid),'state':state,'age_seconds':int(age),'name':name})
 command='for n in cpu.max memory.max memory.current memory.peak memory.events cpuset.cpus.effective; do p=/sys/fs/cgroup/$n; if [ -f "$p" ]; then printf "%s\\n" "$n"; cat "$p"; fi; done'
 limits=read(['exec',container,'sh','-c',command])
 oom=read(['inspect','--format','{{json .State.OOMKilled}}',container])
 rows.append({'container_id':container,'top_exit_code':top.returncode,'process_count':len(processes),
  'names':dict(collections.Counter(p['name'] for p in processes)),
  'node_processes':[p for p in processes if 'node' in p['name'].lower() or 'jest' in p['name'].lower()],
  'cgroup_read_exit_code':limits.returncode,'cgroup_raw':limits.stdout,
  'container_oom_killed':json.loads(oom.stdout) if oom.returncode==0 else None})
print(json.dumps({'run_id':RUN_ID,'observed_epoch':time.time(),'owned_containers':rows}))
'''.replace('RUN_ID', repr(args.run_id))
    with connect_controller(config_file=args.config) as endpoint:
        with rpc_client(endpoint.url, endpoint.credentials, timeout_ms=60000) as client:
            result = client.exec_in_container(controller_pb2.Controller.ExecInContainerRequest(
                task_id='/exedev/' + args.run_id + '/0',
                command=['bash', '-c', 'exec "$IRIS_PYTHON" -c "$1"', '_', outer], timeout_seconds=55))
    assert result.exit_code == 0 and not result.error, (result.exit_code, result.error)
    report = json.loads(result.stdout)
    report.update(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), read_only=True,
        scope='Exact-label owned containers, process names/ages and cgroup accounting only. No command bodies, environment values, signals, test runs, model calls or mutations.',
        limitations='One snapshot; no attribution of slowdown, worker policy or task yield from process counts alone. Container OOM state and cgroup memory.events have different scopes.')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
