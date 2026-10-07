"""Metadata-only scan of the fixed issue-5 repository revisions; no source execution."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'observations.jsonl'
def now():return datetime.now(timezone.utc).isoformat()
def guard(start=False):
    available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    load=os.getloadavg()[0]
    assert available >= (2.5 if start else 2)*1024**3 and load < (1.5 if start else 2.5),(available,load)
    if start:assert available-180*1024**2>=2*1024**3
    return {'available_bytes':available,'load1':load}

def main():
    initial=guard(True);started=now();exit_status=1;completed=0
    inventory=json.loads((ROOT/'inventory.json').read_text())
    saved={x['source_id']:x for x in (json.loads(l) for l in OUT.read_text().splitlines())} if OUT.exists() else {}
    try:
        with OUT.open('a') as output:
            for item in inventory:
                if not item['repo'] or item['source_id'] in saved:continue
                guard();t=time.monotonic();rec={**item,'observed_at':now(),'status':'unknown','notebooks':[]}
                endpoint=f"repos/{item['repo']}/git/trees/{item['revision']}?recursive=1"
                with tempfile.TemporaryFile() as body:
                    try:
                        proc=subprocess.run(['gh','api',endpoint],stdout=body,stderr=subprocess.PIPE,timeout=25)
                        size=body.tell();rec['response_bytes']=size
                        if size>16*1024**2:rec['error']='Response exceeded 16 MiB parsing cap'
                        else:
                            body.seek(0);raw=body.read();rec['response_sha256']=hashlib.sha256(raw).hexdigest()
                            if proc.returncode:
                                rec['error']=proc.stderr.decode(errors='replace')[:1200]
                            else:
                                data=json.loads(raw);rec['tree_sha']=data.get('sha');rec['truncated']=data.get('truncated',True)
                                tree=data.get('tree',[]);rec['entries_received']=len(tree)
                                rec['submodules']=sum(x.get('type')=='commit' for x in tree)
                                rec['notebooks']=[{'path':x['path'],'sha':x['sha'],'size':x.get('size')} for x in tree if x.get('type')=='blob' and x['path'].lower().endswith('.ipynb') and '.ipynb_checkpoints' not in x['path'].split('/')]
                                rec['status']='present' if rec['notebooks'] else ('unknown' if rec['truncated'] else 'absent')
                                rec['notebook_count_complete']=not rec['truncated']
                    except (subprocess.TimeoutExpired,json.JSONDecodeError) as e:rec['error']=str(e)[:1000]
                rec['elapsed_seconds']=round(time.monotonic()-t,3);rec['finished_at']=now()
                output.write(json.dumps(rec)+'\n');output.flush();completed+=1
                if completed%25==0:print(json.dumps({'newly_scanned':completed,'last_repo':item['repo'],'last_status':rec['status'],'resources':guard()}),flush=True)
                if 'rate limit' in rec.get('error','').lower():raise RuntimeError('Rate limit; stopped without retries')
            exit_status=0
    finally:
        log={'start':started,'end':now(),'exit_status':exit_status,'newly_scanned':completed,'estimate_mib':180,'peak_self_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'initial_resources':initial,'final_resources':guard()}
        with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
        print(json.dumps(log),flush=True)
if __name__=='__main__':main()
