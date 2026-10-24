"""Self-authored diagnostic writer; never a biological verifier."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

ROOT=Path('/logs/verifier')
EVENTS=ROOT/'process-events.jsonl'


def process(pid):
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();fields=raw.rsplit(')',1)[1].split()
        info=Path(f'/proc/{pid}/fdinfo/1').read_text()
        stat=os.stat(f'/proc/{pid}/fd/1')
        cmd=Path(f'/proc/{pid}/cmdline').read_bytes()
        return dict(pid=pid,state=fields[0],start_ticks=int(fields[19]),fd1_inode=stat.st_ino,fd1_size=stat.st_size,
            fd1_offset=int(re.search(r'^pos:\s*(\d+)',info,re.M)[1]),writer_command=b'/tests/writer.py' in cmd,
            command_sha256=hashlib.sha256(cmd).hexdigest())
    except (OSError,ValueError,IndexError,TypeError):return dict(pid=pid,unavailable=True)


def append(event,previous=False):
    fd=os.open(EVENTS,os.O_RDWR|os.O_CREAT|os.O_APPEND,0o644)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        event.update(monotonic_ns=time.monotonic_ns(),wall_ns=time.time_ns())
        if previous:
            os.lseek(fd,0,os.SEEK_SET);raw=os.read(fd,256*1024+1);assert len(raw)<=256*1024
            old=[json.loads(line) for line in raw.splitlines()]
            event['previous']=[dict(expected_pid=row['pid'],expected_start_ticks=row['self']['start_ticks'],
                expected_token=row['token'],observed=process(row['pid'])) for row in old if row['event']=='start']
        os.write(fd,(json.dumps(event,separators=(',',':'))+'\n').encode())
    finally:os.close(fd)


def main():
    seconds=float(os.environ['FIXTURE_WRITER_SECONDS']);assert seconds in [2.0,30.0]
    assert re.fullmatch(r'biotasks41-[a-z0-9-]+',os.environ['BIOTASKS_RUN_ID'])
    token=uuid.uuid4().hex;pid=os.getpid();self_info=process(pid);assert not self_info.get('unavailable')
    limits={}
    for key in ['cpu.max','memory.max']:
        path=Path('/sys/fs/cgroup')/key;limits[key]=path.read_text().strip() if path.exists() else None
    append(dict(event='start',token=token,pid=pid,ppid=os.getppid(),pgrp=os.getpgrp(),session=os.getsid(0),
        self=self_info,writer_seconds=seconds,cgroup=limits),previous=True)
    start=time.monotonic();number=0
    while time.monotonic()-start<seconds:
        prefix=(token+':'+format(number,'08d')+':').encode();record=prefix+b'x'*(1023-len(prefix))+b'\n'
        assert len(record)==1024;os.write(1,record);number+=1
        if number%10==0:
            snapshot=(ROOT/'writer.log').read_bytes();assert len(snapshot)<2*1024**2
            append(dict(event='sample',token=token,pid=pid,self=process(pid),log_bytes=len(snapshot),
                log_nul_bytes=snapshot.count(b'\0'),log_sha256=hashlib.sha256(snapshot).hexdigest()))
        time.sleep(0.1)
    append(dict(event='end',token=token,pid=pid,records=number,self=process(pid)))


if __name__=='__main__':main()
