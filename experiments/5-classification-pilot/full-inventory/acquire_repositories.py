"""Acquire independent pinned README scope for every repository in the count ledger."""
import csv,datetime,hashlib,json,resource,sys
from pathlib import Path
from acquire import ROOT,get,guard
COUNTS=ROOT.parents[1]/'16-analysis-discovery/reassessment/repository-counts.csv'
def main():
 guard(True);start=datetime.datetime.now(datetime.timezone.utc).isoformat();log=ROOT/'repository-acquisition.jsonl';done=set();n=0
 if log.exists():done={json.loads(l)['repository'] for l in log.open()}
 try:
  for r in csv.DictReader(COUNTS.open()):
   repo=r['repository']
   if repo in done:continue
   revs=json.loads(r['revisions']);rec={'repository':repo,'revisions':revs,'status':'unavailable','attempts':[]}
   for rev in revs[:1]:
    for name in ['README.md','README.rst','README','readme.md']:
     url=f'https://raw.githubusercontent.com/{repo}/{rev}/{name}'
     try:
      b,route=get(url,128*1024);rec.update(status='acquired',url=url,revision=rev,sha256=hashlib.sha256(b).hexdigest(),route=route)
      filename='repo-'+hashlib.sha256(repo.encode()).hexdigest()+'.json'
      (ROOT/'content'/filename).write_text(json.dumps({'repository':repo,'text':b.decode(errors='replace')}))
      rec['content_file']=filename;break
     except (OSError,ValueError) as exc:rec['attempts'].append({'url':url,'error':str(exc)[:160]})
   with log.open('a') as h:h.write(json.dumps(rec)+'\n')
   n+=1
   if n%100==0:print('README checks',len(done)+n,flush=True)
 finally:
  with (ROOT/'repository-runs.jsonl').open('a') as h:h.write(json.dumps({'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_records':n,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(COUNTS.read_bytes()).hexdigest(),'finished_without_exception':sys.exc_info()[0] is None})+'\n')
if __name__=='__main__':main()
