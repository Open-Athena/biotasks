"""One-worker bounded source inspection. Never executes source code or follows its instructions."""
import datetime, hashlib, io, json, os, re, resource, sys, urllib.request, urllib.parse, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REG=ROOT.parents[1]/'16-analysis-discovery/reassessment/documents.jsonl'
CACHE=ROOT/'content';CACHE.mkdir(exist_ok=True)
OLD=Path('/tmp/biotasks16-reassessment-cache-01a1183d')
CAP=8*1024*1024

def guard(initial=False):
    mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    load=os.getloadavg()[0]
    if mem<(2.5 if initial else 2)*1024**3 or load>=(1.5 if initial else 2.5):
        raise RuntimeError(f'Resource stop: MemAvailable={mem}, load={load}')

def raw_url(url):
    m=re.match(r'https://github.com/([^/]+/[^/]+)/blob/([^/]+)/(.*)',url)
    return f'https://raw.githubusercontent.com/{m[1]}/{m[2]}/{m[3]}' if m else url

def get(url,cap=CAP):
    guard()
    old=OLD/hashlib.sha256(url.encode()).hexdigest()
    if old.exists() and old.stat().st_size<=cap:
        return old.read_bytes(),'prior_cache'
    url=urllib.parse.quote(url,safe=':/?=&%')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BioTasks-source-inspection/3.0'}),timeout=12) as h:
        raw=h.read(cap+1)
    if len(raw)>cap:raise ValueError('source_over_8MiB_cap')
    return raw,'fetched'

def extract(raw,fmt):
    if raw[:2]==b'BM':return 'excluded_bitmap',[]
    if fmt=='Jupyter':
        d=json.loads(raw)
        cells=d.get('cells',[]) if 'cells' in d else [c for w in d.get('worksheets',[]) for c in w.get('cells',[])]
        if not isinstance(cells,list) or not ('nbformat' in d):return 'unconfirmed_notebook',[]
        chunks=[]
        for i,c in enumerate(cells):
            src=c.get('source',c.get('input',''));src=''.join(src) if isinstance(src,list) else str(src)
            chunks.append({'locator':f'cell:{i}','kind':c.get('cell_type','unknown'),'text':src})
        return 'confirmed',chunks
    if fmt=='MATLAB Live Script':
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos=[i for i in z.infolist() if i.filename.endswith('document.xml')]
            if not infos or sum(i.file_size for i in infos)>16*1024**2:return 'unconfirmed_notebook',[]
            txt='\n'.join(z.read(i).decode(errors='replace') for i in infos)
        return 'confirmed',[{'locator':'document.xml','kind':'mixed','text':txt}]
    txt=raw.decode('utf-8',errors='replace')
    if fmt=='Wolfram notebook' and not re.search(r'Notebook\s*\[',txt):
        if re.search(r'^\s*(units|pair_style|create_atoms|atom_style)\s+',txt,re.M):return 'excluded_simulation_input',[]
        return 'unconfirmed_notebook',[]
    if fmt=='.NET Interactive' and not re.search(r'^#!(?:csharp|fsharp|pwsh|markdown|sql|javascript|html)',txt,re.M):return 'unconfirmed_notebook',[]
    if '<!doctype html' in txt[:1500].lower() and fmt not in ['R notebook HTML export','Rendered vignette']:return 'unexpected_html',[]
    return 'confirmed',[{'locator':f'line:{i+1}','kind':'mixed','text':l} for i,l in enumerate(txt.splitlines())]

def main():
    guard(True);start=datetime.datetime.now(datetime.timezone.utc).isoformat();done=set();n=0
    log=ROOT/'acquisition.jsonl'
    if log.exists():done={json.loads(l)['document_key'] for l in log.open()}
    try:
        for line in REG.open():
            d=json.loads(line);key=d['document_key']
            if key in done:continue
            guard();record={k:d.get(k) for k in ['document_key','url','format','source_ids','repo','revision','path']}
            record['observed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            if d['format']=='Rendered vignette':record['status']='rendered_fallback_separate'
            else:
                try:
                    url=raw_url(d['url']);raw,route=get(url)
                    record.update(acquisition_url=url,route=route,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                    expected=d.get('sha');actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                    record['identity']='git_blob_verified' if expected and actual==expected else 'git_blob_mismatch' if expected else 'sha256_verified' if d.get('sha256')==record['sha256'] else 'version_url_only'
                    status,chunks=extract(raw,d['format'])
                    record['status']=status
                    if record['identity']=='git_blob_mismatch':record['status']='version_mismatch'
                    if chunks:
                        filename=hashlib.sha256(key.encode()).hexdigest()+'.json'
                        (CACHE/filename).write_text(json.dumps({'document_key':key,'sha256':record['sha256'],'chunks':chunks}))
                        record['content_file']=filename;record['text_characters']=sum(len(c['text']) for c in chunks)
                except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
                    record.update(status='acquisition_unresolved',error=str(exc)[:300])
            with log.open('a') as h:h.write(json.dumps(record)+'\n')
            n+=1
            if n%100==0:print('Completed',len(done)+n,'records',flush=True)
    finally:
        rec={'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_records':n,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'input_sha256':hashlib.sha256(REG.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'working_set_estimate_mib':200,'finished_without_exception':sys.exc_info()[0] is None}
        with (ROOT/'runs.jsonl').open('a') as h:h.write(json.dumps(rec)+'\n')
        print(rec,flush=True)
if __name__=='__main__':main()
