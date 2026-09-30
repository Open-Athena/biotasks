import datetime,hashlib,json,subprocess
from pathlib import Path
p=Path('/tmp/bio-discovery-20260929/top100');f=p/'github-source-metadata.json';d=json.loads(f.read_text());records={r['requested_name'].lower():r for r in d['records']};new={}
for file in sorted((p/'github-search').glob('*.json')):
 if '.provenance.' in file.name:continue
 for r in json.loads(file.read_text())['items']:
  name=r['full_name'];key=name.lower();origin='github-search:'+file.stem
  if key in records:
   if origin not in records[key]['discovery_sources']:records[key]['discovery_sources'].append(origin)
  else:
   new.setdefault(key,{'requested_name':name,'discovery_sources':[]})['discovery_sources'].append(origin)
requests=list(new.values());fields='nameWithOwner url description stargazerCount isArchived isFork homepageUrl defaultBranchRef { name target { oid } } repositoryTopics(first:100) { totalCount pageInfo { hasNextPage } nodes { topic { name } } }'
for offset in range(0,len(requests),60):
 batch=requests[offset:offset+60];query='query {'+'\n'.join(f'r{i}: repository(owner:{json.dumps(r["requested_name"].split("/")[0])},name:{json.dumps(r["requested_name"].split("/")[1])}) {{ {fields} }}' for i,r in enumerate(batch))+'}'
 key=hashlib.sha256(query.encode()).hexdigest()[:16];req=p/'github-metadata'/(key+'.request.json');resp=p/'github-metadata'/(key+'.response.json');req.write_text(json.dumps({'query':query})+'\n')
 if not resp.exists():
  proc=subprocess.run(['gh','api','graphql','--input',str(req)],capture_output=True,timeout=60);assert proc.returncode==0,proc.stderr;resp.write_bytes(proc.stdout)
 result=json.loads(resp.read_bytes());assert not result.get('errors')
 for i,r in enumerate(batch):r['metadata']=result['data'][f'r{i}'];r['response_sha256']=hashlib.sha256(resp.read_bytes()).hexdigest();d['records'].append(r)
 print('Added metadata',min(offset+60,len(requests)),'/',len(requests),flush=True)
d['search_expansion_at']=datetime.datetime.now(datetime.UTC).isoformat();f.write_text(json.dumps(d,indent=2)+'\n')
(p/'github-request-sources.json').write_text(json.dumps([{k:r[k] for k in ['requested_name','discovery_sources']} for r in d['records']],indent=2)+'\n')
