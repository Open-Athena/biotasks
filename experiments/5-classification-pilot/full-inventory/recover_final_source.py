"""Known 72,238,389-byte notebook: bounded 96 MiB streaming retry."""
import datetime,hashlib,json,resource,urllib.request
import recover
from acquire import ROOT,REG,guard,raw_url
start=datetime.datetime.now(datetime.timezone.utc).isoformat();guard(True)
key='github:3dmol/3dmol.js:py3Dmol/volumetric.ipynb'
r=next(json.loads(l) for l in (ROOT/'acquisition.jsonl').open() if json.loads(l)['document_key']==key)
d=next(json.loads(l) for l in REG.open() if json.loads(l)['document_key']==key)
assert d['size']==72238389
recover.STREAM_CAP=96*1024**2
chunks,f=recover.stream(raw_url(r['url']))
assert f.n==d['size'] and f.git.hexdigest()==d['sha']
r.update(status='confirmed',sha256=f.digest.hexdigest(),bytes=f.n,identity='git_blob_verified',route='streamed_ijson_3.5.1_96MiB_cap')
r.pop('error',None);r['content_file']=hashlib.sha256(key.encode()).hexdigest()+'.json'
(ROOT/'content'/r['content_file']).write_text(json.dumps({'document_key':key,'sha256':r['sha256'],'chunks':chunks}))
with (ROOT/'recovery.jsonl').open('a') as h:h.write(json.dumps(r)+'\n')
# Verify the suspected script collision from its complete, bounded original bytes.
key='github:soft-matter/trackpy:benchmarks/maxima_benchmarks.ipynb'
r=next(json.loads(l) for l in (ROOT/'acquisition.jsonl').open() if json.loads(l)['document_key']==key)
with urllib.request.urlopen(r['acquisition_url'],timeout=12) as h:b=h.read(1024*1024+1)
assert len(b)<1024*1024 and b.startswith(b'# must be run in ipython')
assert b'# %%' not in b and b'# In[' not in b and b'nbformat' not in b
r.update(status='excluded_plain_script',sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),rationale='Complete source is a plain Python benchmark without notebook JSON or percent/In cell markers.')
with (ROOT/'format-corrections.jsonl').open('a') as h:h.write(json.dumps(r)+'\n')
(ROOT/'final-source-recovery.json').write_text(json.dumps({'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'working_set_estimate_mib':250,'notebook_bytes':f.n,'notebook_git_blob_verified':True,'plain_script_bytes':len(b),'exit_status':0},indent=2)+'\n')
print('Recovered full notebook and verified plain-script exclusion.')
