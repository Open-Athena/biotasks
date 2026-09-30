import csv,datetime,hashlib,heapq,json,re,subprocess
from pathlib import Path
root=Path('/tmp/bio-discovery-20260929')
out=root/'top100'
cache=out/'github-metadata'
cache.mkdir(exist_ok=True)
sources={}
def add(text,origin):
    for slug in re.findall(r'https?://(?:www\.)?github.com/([\w.-]+/[\w.-]+)',text or ''):
        slug=slug.removesuffix('.git').rstrip('.')
        if slug.split('/')[0].lower() in {'features','topics','collections','settings','orgs','users','sponsors','marketplace'}:continue
        sources.setdefault(slug.lower(),{'requested_name':slug,'discovery_sources':[]})['discovery_sources'].append(origin)
meta={r['project']:r for r in json.loads((out/'pypi-metadata-search.json').read_text())['data']}
for rank,row in enumerate(json.loads((out/'pypi-counts-without-mirrors.json').read_text())['data'],1):
    m=meta[row['project']]['metadata']
    add(' '.join([m[3]]+m[4]),'pypi:'+row['project'])
bioc=json.loads((root/'bioconductor-metadata.json').read_text())
with (root/'bioconductor-scores.tsv').open() as f:
    ranked=heapq.nlargest(150,csv.DictReader(f,delimiter='\t'),key=lambda r:int(r['Download_score']))
for row in ranked:
    record=bioc.get(row['Package'],{})
    add(' '.join(record.get(k,'') for k in ['URL','BugReports']),'bioconductor:'+row['Package'])
for row in json.loads((out/'bioconda-screen.json').read_text())['records']:
    if row.get('exclusion'):continue
    text=' '.join(row.get(k,'') for k in ['home','dev_url','doc_url'])
    text+=' '+' '.join('https://github.com/'+slug for slug in row.get('source_github_links',[]))
    add(text,'bioconda:'+row['package'])
for file in (out/'github-search').glob('*.json'):
    if '.provenance.' in file.name:continue
    for row in json.loads(file.read_text())['items']:add(row['html_url'],'github-search:'+file.stem)
for row in json.loads(Path('docs/experiments/bio-task-generation/01-discovery/inventory.json').read_text())['candidates']:
    if row.get('github_metadata'):add('https://github.com/'+row['github_metadata']['full_name'],'baseline95:'+row['name'])
# Known-source coverage checks documented separately from the search-derived pool.
for slug in ['google-deepmind/alphafold','google-deepmind/alphafold3']:
    add('https://github.com/'+slug,'manual-known-source-check')
requests=list(sources.values())
(out/'github-request-sources.json').write_text(json.dumps(requests,indent=2)+'\n')
all_rows=[]
for start in range(0,len(requests),75):
    batch=requests[start:start+75]
    query='query {\n'+'\n'.join(f'r{i}: repository(owner:{json.dumps(r["requested_name"].split("/")[0])},name:{json.dumps(r["requested_name"].split("/")[1])}) {{ nameWithOwner url description stargazerCount isArchived isFork homepageUrl defaultBranchRef {{ name target {{ oid }} }} repositoryTopics(first:100) {{ totalCount pageInfo {{ hasNextPage }} nodes {{ topic {{ name }} }} }} }}' for i,r in enumerate(batch))+'\n}'
    key=hashlib.sha256(query.encode()).hexdigest()[:16]
    payload_file=cache/(key+'.request.json')
    response_file=cache/(key+'.response.json')
    payload_file.write_text(json.dumps({'query':query})+'\n')
    if not response_file.exists():
        proc=subprocess.run(['gh','api','graphql','--input',str(payload_file)],capture_output=True,timeout=60)
        try:response=json.loads(proc.stdout)
        except json.JSONDecodeError:raise RuntimeError(proc.stderr.decode())
        assert 'data' in response, response.get('errors')
        assert all(e.get('type')=='NOT_FOUND' for e in response.get('errors',[])),response.get('errors')
        response_file.write_bytes(proc.stdout)
    response=json.loads(response_file.read_text())
    for i,r in enumerate(batch):
        data=response['data'][f'r{i}']
        if data:
            assert not data['repositoryTopics']['pageInfo']['hasNextPage']
        all_rows.append({**r,'metadata':data,'response_sha256':hashlib.sha256(response_file.read_bytes()).hexdigest()})
    print('Github metadata',min(start+75,len(requests)),'/',len(requests),flush=True)
(out/'github-source-metadata.json').write_text(json.dumps({'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'records':all_rows},indent=2)+'\n')
print('Complete:',len(all_rows),'queried;',sum(r['metadata'] is not None for r in all_rows),'resolved',flush=True)
