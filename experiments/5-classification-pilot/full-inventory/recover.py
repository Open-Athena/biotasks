"""Recover oversized notebooks with event parsing; preserve bounded failures."""
import hashlib,json,sys,urllib.request,urllib.parse,datetime,resource
from pathlib import Path
sys.path.insert(0,'/tmp/biotasks-classification-ijson-351')
import ijson
from acquire import ROOT,REG,guard,raw_url,extract,get
class Reader:
 def __init__(self,h):
  self.h=h;self.n=0;self.digest=hashlib.sha256();self.length=int(h.headers.get('Content-Length','0'));self.git=hashlib.sha1(b'blob '+str(self.length).encode()+b'\0')
 def read(self,size=-1):
  guard();b=self.h.read(size);self.n+=len(b)
  if self.n>64*1024**2:raise ValueError('stream_over_64MiB_cap')
  self.digest.update(b);self.git.update(b);return b

def stream(url):
 with urllib.request.urlopen(urllib.parse.quote(url,safe=':/?=&%'),timeout=15) as h:
  f=Reader(h);chunks=[];cell=None;nbformat=None
  for prefix,event,value in ijson.parse(f):
   if prefix=='nbformat' and event=='number':nbformat=int(value)
   if prefix in ['cells.item','worksheets.item.cells.item']:
    if event=='start_map':cell={'locator':f'cell:{len(chunks)}','kind':'unknown','text':''}
    elif event=='end_map' and cell is not None:chunks.append(cell);cell=None
   if cell is not None:
    if prefix in ['cells.item.cell_type','worksheets.item.cells.item.cell_type'] and event=='string':cell['kind']=value
    if prefix in ['cells.item.source','cells.item.source.item','worksheets.item.cells.item.input','worksheets.item.cells.item.input.item','worksheets.item.cells.item.source','worksheets.item.cells.item.source.item'] and event=='string':cell['text']+=value
  if not nbformat:raise ValueError('no_nbformat')
  return chunks,f

def main():
 guard(True);start=datetime.datetime.now(datetime.timezone.utc).isoformat();launch_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();latest={json.loads(l)['document_key']:json.loads(l) for l in (ROOT/'acquisition.jsonl').open()};out=ROOT/'recovery.jsonl';done=set();n=0
 if out.exists():done={json.loads(l)['document_key'] for l in out.open()}
 manifest={json.loads(l)['document_key']:json.loads(l) for l in REG.open()}
 try:
  for key,r in latest.items():
   if r['status']!='acquisition_unresolved' or key in done:continue
   guard();rec=dict(r);rec['previous_error']=r.get('error');url=raw_url(r['url'].replace('https://www.github.com/','https://github.com/'));rec['acquisition_url']=url
   try:
    if r.get('error')=='source_over_8MiB_cap':
     chunks,f=stream(url);rec.update(status='confirmed',sha256=f.digest.hexdigest(),bytes=f.n,route='streamed_ijson_3.5.1')
     expected=manifest.get(key,{}).get('sha');rec['identity']='git_blob_verified' if expected and f.n==f.length and f.git.hexdigest()==expected else 'pinned_url_streamed' if r.get('revision') else 'version_url_only'
    else:
     raw,route=get(url)
     if raw.startswith(b'version https://git-lfs.github.com/spec/'):
      rec.update(status='git_lfs_pointer',pointer=raw.decode()[:300]);chunks=[]
     else:
      rec['prefix_preview']=repr(raw[:120]);status,chunks=extract(raw,r['format']);rec.update(status=status,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),route=route,identity='version_url_only')
    if chunks:
     filename=hashlib.sha256(key.encode()).hexdigest()+'.json';(ROOT/'content'/filename).write_text(json.dumps({'document_key':key,'sha256':rec['sha256'],'chunks':chunks}));rec['content_file']=filename
    rec.pop('error',None)
   except (OSError,ValueError,ijson.JSONError) as exc:rec['status']='acquisition_unresolved';rec['error']=str(exc)[:250]
   with out.open('a') as h:h.write(json.dumps(rec)+'\n')
   n+=1
   if n%10==0:print('Recovery checks',n,flush=True)
 finally:
  with (ROOT/'recovery-runs.jsonl').open('a') as h:h.write(json.dumps({'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_records':n,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'script_sha256':launch_hash,'parser':'ijson==3.5.1','python':sys.version,'working_set_estimate_mib':250,'finished_without_exception':sys.exc_info()[0] is None})+'\n')
if __name__=='__main__':main()
