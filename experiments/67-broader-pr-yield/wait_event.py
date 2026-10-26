"""Wait for task-owned lifecycle events using inotify; no status/API polling."""
import ctypes
import json
from pathlib import Path
import select
import struct

root=Path(__file__).resolve().parent
active=json.loads((root/'active-workflow.json').read_text());work=root/active['work_dir']
manifest=json.loads((root/active['manifest']).read_text())
paths={work,root/'inputs-private',Path(manifest['budget_ledger']).parent}
for case in manifest['cases']:
    gen=Path(case['generation_root']) if case.get('mode')=='completed' else work/case['id']
    for p in [gen,gen/'runs',gen/'runs/generation',gen/'runs/generation/cleanup',gen/'runs/generation/stop']:
        paths.add(p)
    val=work/(case['id']+'-handoff')/'validation';paths.update([val.parent,val,val/'runs'])
    if (val/'runs').is_dir():
        for d in (val/'runs').iterdir():
            if d.is_dir():paths.update([d,d/'cleanup',d/'stop'])
lib=ctypes.CDLL(None,use_errno=True);fd=lib.inotify_init1(0x800|0x80000)
if fd<0:raise OSError(ctypes.get_errno(),'inotify_init1')
watched={}
for p in paths:
    if p.is_dir() and not p.is_symlink():
        wd=lib.inotify_add_watch(fd,str(p).encode(),0x8|0x80|0x100|0x400|0x800)
        if wd<0:raise OSError(ctypes.get_errno(),'inotify_add_watch')
        watched[wd]=p
import os
import time
end=time.monotonic()+55
out=[]
while not out:
    remaining=end-time.monotonic()
    if remaining<=0 or not select.select([fd],[],[],remaining)[0]:
        print(json.dumps({'event':'idle','status_poll':False}));raise SystemExit(0)
    raw=os.read(fd,65536);offset=0
    while offset<len(raw):
        wd,mask,cookie,size=struct.unpack_from('iIII',raw,offset);offset+=16
        name=raw[offset:offset+size].split(b'\0',1)[0].decode();offset+=size
        if (mask&0x40000000 and work in watched.get(wd,Path('/')).parents) or name in ['budget.json','journal.json','readback.json','cleanup-proof.json','held.json','accounting.json','model-accounting.json','controller-output-003.log','dendropy-generation-controller.log','anndata-generation-controller.log','biopython-generation-controller.log']:
            out.append({'directory':str(watched.get(wd,'')),'name':name,'mask':mask})
import monitor
value=monitor.snapshot()
print(json.dumps({'event':'lifecycle_change','changes':out,'snapshot':value,'status_poll':False}))
