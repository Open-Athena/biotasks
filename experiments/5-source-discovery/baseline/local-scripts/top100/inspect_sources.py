import datetime,hashlib,json,subprocess
from pathlib import Path
p=Path('/tmp/bio-discovery-20260929/top100')
d=json.loads((p/'cohorts-provisional.json').read_text())
extra=[r['source_id'].removeprefix('github:') for r in d['sources'] if r['source_id'].startswith('github:') and not r['github']]
extra += ['OpenMS/OpenMS','biocore/biom-format','mapping-commons/sssom-py','bp-kelley/descriptastorus','ccsb-scripps/AutoDock-Vina','mdtraj/mdtraj','gprofiler/gprofiler-official']
review=['K-Dense-AI/scientific-agent-skills','aipoch/medical-research-skills','jeshraghian/snntorch','deepmodeling/deepmd-kit','jax-md/jax-md','lammps/lammps','microsoft/Graphormer','greenelab/deep-review','sib-swiss/training-collection','scorpiolea/AiCE','soft-matter/trackpy','silx-kit/fabio','seung-lab/connected-components-3d','aipoch/open-science','synthetic-sciences/openscience']
names=list(dict.fromkeys(extra+review)); fields='nameWithOwner url description stargazerCount isArchived isFork homepageUrl defaultBranchRef { name target { oid } } repositoryTopics(first:100) { totalCount pageInfo { hasNextPage } nodes { topic { name } } }'
query='query {'+'\n'.join(f'r{i}: repository(owner:{json.dumps(n.split("/")[0])},name:{json.dumps(n.split("/")[1])}) {{ {fields} }}' for i,n in enumerate(names))+'}'
f=p/'github-extra-request.json';f.write_text(json.dumps({'query':query})+'\n')
response=subprocess.run(['gh','api','graphql','--input',str(f)],capture_output=True,timeout=60)
raw=json.loads(response.stdout);assert 'data' in raw;assert all(e['type']=='NOT_FOUND' for e in raw.get('errors',[]));(p/'github-extra-response.json').write_bytes(response.stdout)
allmeta=json.loads((p/'github-source-metadata.json').read_text()); existing={r['requested_name'].lower() for r in allmeta['records']}
for i,n in enumerate(names):
 m=raw['data'][f'r{i}'];print(n,'->',m['nameWithOwner'] if m else None,flush=True)
 if n.lower() not in existing:allmeta['records'].append({'requested_name':n,'metadata':m,'discovery_sources':['manual-source-identity-check'],'response_sha256':hashlib.sha256(response.stdout).hexdigest()})
allmeta['identity_update_at']=datetime.datetime.now(datetime.UTC).isoformat();(p/'github-source-metadata.json').write_text(json.dumps(allmeta,indent=2)+'\n')
folder=p/'readmes';folder.mkdir(exist_ok=True)
for n in review:
 f=folder/(n.replace('/','__').lower()+'.json')
 if f.exists():continue
 proc=subprocess.run(['gh','api',f'repos/{n}/readme'],capture_output=True,timeout=30)
 assert proc.returncode==0,proc.stderr
 assert len(proc.stdout)<2_000_000
 f.write_bytes(proc.stdout)
 print('README',n,flush=True)
