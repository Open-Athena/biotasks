import datetime,hashlib,json,subprocess
from pathlib import Path
r=Path('/tmp/bio-discovery-20260929/top200');cache=r/'github-metadata';cache.mkdir(exist_ok=True)
d=json.loads((r/'cohorts-provisional.json').read_text());gh=json.loads((r/'github-source-metadata.json').read_text())
known={x['requested_name'].lower() for x in gh['records'] if x['metadata']}
known|={x['metadata']['nameWithOwner'].lower() for x in gh['records'] if x['metadata']}
requests=[{'requested_name':s['source_id'][7:],'discovery_sources':['top200-identity-only']} for s in d['sources'] if s['source_id'].startswith('github:') and s['source_id'][7:] not in known]
for start in range(0,len(requests),50):
 batch=requests[start:start+50]
 query='query {\n'+'\n'.join(f'r{i}: repository(owner:{json.dumps(x["requested_name"].split("/")[0])},name:{json.dumps(x["requested_name"].split("/")[1])}) {{ nameWithOwner url description stargazerCount isArchived isFork homepageUrl defaultBranchRef {{ name target {{ oid }} }} repositoryTopics(first:100) {{ totalCount pageInfo {{ hasNextPage }} nodes {{ topic {{ name }} }} }} }}' for i,x in enumerate(batch))+'\n}'
 key=hashlib.sha256(query.encode()).hexdigest()[:16];req=cache/(key+'.request.json');resp=cache/(key+'.response.json');req.write_text(json.dumps({'query':query})+'\n')
 if not resp.exists():
  p=subprocess.run(['gh','api','graphql','--input',str(req)],capture_output=True,timeout=60)
  response=json.loads(p.stdout);assert 'data' in response,p.stderr.decode();assert all(e.get('type')=='NOT_FOUND' for e in response.get('errors',[])),response.get('errors');resp.write_bytes(p.stdout)
 response=json.loads(resp.read_text())
 for i,x in enumerate(batch):
  m=response['data'][f'r{i}'];assert not m or not m['repositoryTopics']['pageInfo']['hasNextPage']
  gh['records'].append({**x,'metadata':m,'response_sha256':hashlib.sha256(resp.read_bytes()).hexdigest()})
  print(x['requested_name'],'=>',m['nameWithOwner'] if m else 'NOT FOUND',flush=True)
gh['top200_identity_observed_at']=datetime.datetime.now(datetime.UTC).isoformat()
(r/'github-source-metadata.json').write_text(json.dumps(gh,indent=2)+'\n')
