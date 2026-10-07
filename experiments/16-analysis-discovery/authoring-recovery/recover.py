"""Recover authoring documents behind every recorded rendered vignette, without execution."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import tarfile
import urllib.request
from urllib.parse import urlsplit, urljoin
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
FORMATS={'.Rmd':'R Markdown','.Rnw':'Sweave/knitr','.qmd':'Quarto','.Rtex':'Sweave/knitr'}
def now():return datetime.now(timezone.utc).isoformat()
def guard(start=False):
    mem=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    assert mem>=(2.5 if start else 2)*1024**3 and os.getloadavg()[0]<(1.5 if start else 2.5)
    if start:assert mem-150*1024**2>2*1024**3

def fetch(url,record,cap=1024**2):
    guard();r={'url':url};record['requests'].append(r)
    try:
        with urllib.request.urlopen(url,timeout=12) as response:
            b=response.read(cap+1);r.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),final_url=response.url)
        if len(b)>cap:raise ValueError('byte cap exceeded: '+str(cap))
        return b
    except Exception as e:r['error']=str(e)[:400];return None

def valid(b,ext):
    t=b.decode(errors='replace')
    if re.search(r'<(?:!doctype html|html)',t[:500],re.I):return False
    if ext in ('.Rnw','.Rtex'):return '\\VignetteEngine' in t or bool(re.search(r'<<.*?>>=',t))
    return '\\VignetteEngine' in t or bool(re.search(r'```\s*\{r[ ,}]',t))

def source(rendered,url,path,b,ext,how):
    return {'url':url,'path':path,'format':FORMATS[ext],'group_url':rendered['url'],'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'detection':how}

def main():
    guard(True);start=now();code=1
    items=json.loads((ROOT.parent/'alternative-source-audit/summary.json').read_text())['rows']
    out=ROOT/'observations.jsonl';seen={json.loads(l)['source_id'] for l in out.read_text().splitlines()} if out.exists() else set()
    try:
        with out.open('a') as f:
            for item in items:
                renders=[n for n in item['documents'] if n['format']=='Rendered vignette']
                if not renders or item['source_id'] in seen:continue
                r={'source_id':item['source_id'],'name':item['name'],'start':now(),'requests':[],'documents':[],'unresolved':[]}
                missing=[]
                for n in renders:
                    stem=str(PurePosixPath(urlsplit(n['url']).path).with_suffix(''));found=False
                    for ext in FORMATS:
                        url='https://bioconductor.posit.co'+stem+ext;b=fetch(url,r)
                        if b is not None and valid(b,ext):
                            r['documents'].append(source(n,url,stem+ext,b,ext,'Fetched authoring text; vignette/chunk syntax verified; paired by versioned stem'));found=True;break
                    if not found:missing.append(n)
                if missing:
                    first=missing[0];parsed=urlsplit(first['url']).path
                    # /packages/3.23/bioc/vignettes/PACKAGE/inst/doc/NAME.html
                    prefix,rest=parsed.split('/vignettes/',1);package=rest.split('/',1)[0]
                    page='https://bioconductor.posit.co'+prefix+'/html/'+package+'.html'
                    raw=fetch(page,r);archive_url=None
                    if raw:
                        match=re.search(r'href=["\']([^"\']*/src/contrib/[^"\']+\.tar\.gz)["\']',raw.decode(errors='replace'))
                        if match:archive_url=urljoin(page,match[1])
                    if archive_url:
                        b=fetch(archive_url,r,16*1024**2)
                        if b:
                            r['archive']={'url':archive_url,'complete':False};total=0;count=0
                            try:
                                with tarfile.open(fileobj=io.BytesIO(b),mode='r|*') as tar:
                                    for m in tar:
                                        total+=m.size;count+=1
                                        if total>64*1024**2 or count>20000:raise ValueError('expanded archive/member cap')
                                        ext=PurePosixPath(m.name).suffix
                                        if not m.isfile() or ext not in FORMATS or m.size>1024**2:continue
                                        if not any(d in m.name for d in ('/vignettes/','/inst/doc/')):continue
                                        targets=[n for n in missing if PurePosixPath(urlsplit(n['url']).path).stem==PurePosixPath(m.name).stem]
                                        if not targets:continue
                                        raw=tar.extractfile(m).read()
                                        if not valid(raw,ext):continue
                                        for n in targets:
                                            if not any(x['group_url']==n['url'] for x in r['documents']):r['documents'].append(source(n,archive_url+'#'+m.name,m.name,raw,ext,'Package archive authoring member; syntax verified; paired by release and stem'))
                                r['archive']['complete']=True
                            except Exception as e:r['archive']['error']=str(e)
                            r['archive'].update(expanded_bytes=total,members=count)
                r['unresolved']=[n for n in renders if not any(x['group_url']==n['url'] for x in r['documents'])]
                r['rendered_count']=len(renders);r['end']=now();f.write(json.dumps(r)+'\n');f.flush()
                print(json.dumps({'name':r['name'],'recovered':len(r['documents']),'unresolved':len(r['unresolved'])}),flush=True)
        code=0
    finally:
        run={'start':start,'end':now(),'exit_status':code,'estimate_mib':150,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps(run)+'\n')
        print(json.dumps(run),flush=True)
if __name__=='__main__':main()
