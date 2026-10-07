"""Inspect archive paths for unresolved guides; no source execution."""
import json,io,tarfile,resource
from pathlib import Path
from recover import ROOT,fetch,guard,now
start=now();guard(True);result=[];code=1
try:
    for line in (ROOT/'final-observations.jsonl').read_text().splitlines():
        r=json.loads(line)
        if not r['unresolved']:continue
        archives=r.get('archive_followups',[])+([r['archive']] if r.get('archive') else [])
        if not archives:continue
        archive=next((a for a in archives if 'tu-dortmund' in a['url']),archives[0])
        rec={'source_id':r['source_id'],'requests':[],'paths':[]};b=fetch(archive['url'],rec,16*1024**2)
        if b:
            total=0
            with tarfile.open(fileobj=io.BytesIO(b),mode='r|*') as t:
                for m in t:
                    total+=m.size
                    if total>64*1024**2:break
                    if '/vignettes/' in m.name or '/inst/doc/' in m.name:
                        rec['paths'].append(m.name)
        result.append(rec);print(r['name'],rec['paths'],flush=True)
    code=0
finally:
    (ROOT/'unresolved-archive-inspection.json').write_text(json.dumps(result,indent=2)+'\n')
    with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps({'pass':'unresolved archive inspection','start':start,'end':now(),'exit_status':code,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'estimate_mib':150})+'\n')
