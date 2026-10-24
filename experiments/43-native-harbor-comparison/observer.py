"""Read-only process/log observation; no verifier writes or termination."""
import json
import subprocess
import time

SCRIPT=r'''
import fcntl,hashlib,importlib.util,json,time
from pathlib import Path
started=time.time_ns();root=Path('/logs/verifier');path=Path('/tests/writer.py')
if not path.exists() or not (root/'process-events.jsonl').exists():
 print(json.dumps(dict(state='awaiting_writer',observed_start_ns=started,observed_finished_ns=time.time_ns())));raise SystemExit
spec=importlib.util.spec_from_file_location('fixture_observation',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with (root/'process-events.jsonl').open('rb') as stream:
 fcntl.flock(stream,fcntl.LOCK_SH);raw=stream.read(256*1024+1)
assert len(raw)<=256*1024
events=[json.loads(line) for line in raw.splitlines()]
starts=[e for e in events if e['event']=='start'];observed=[]
for event in starts:
 observed.append(dict(expected_pid=event['pid'],expected_start_ticks=event['self']['start_ticks'],token=event['token'],observed=module.process(event['pid'])))
log=(root/'writer.log').read_bytes();assert len(log)<2*1024**2
print(json.dumps(dict(state='sampled',observed_start_ns=started,observed_finished_ns=time.time_ns(),processes=observed,
 events_sha256=hashlib.sha256(raw).hexdigest(),event_bytes=len(raw),log_bytes=len(log),log_nul_bytes=log.count(b'\0'),log_sha256=hashlib.sha256(log).hexdigest())))
'''


def snapshot(container):
    started=time.time_ns()
    result=subprocess.run(['/work/real/docker','exec',container,'python3','-B','-c',SCRIPT],capture_output=True,text=True,timeout=5,check=False)
    assert len(result.stdout)<256*1024 and len(result.stderr)<8192
    if result.returncode:
        return dict(state='exec_unavailable',exit_code=result.returncode,observer_started_ns=started,observer_finished_ns=time.time_ns(),stderr=result.stderr[:500])
    value=json.loads(result.stdout);value.update(observer_started_ns=started,observer_finished_ns=time.time_ns());return value
