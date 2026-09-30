import csv,hashlib,json,re
from pathlib import Path

scratch=Path('/tmp/bio-discovery-20260929');root=scratch/'top100'
dest=Path('docs/experiments/bio-task-generation/01-discovery/data');dest.mkdir(exist_ok=True)
stamp='2026-09-29'
d=json.loads((root/'cohorts-provisional.json').read_text())
anns=json.loads((root/'annotations.json').read_text())
selected={r['source_id'] for r in d['sources']}
gh_records=json.loads((root/'github-source-metadata.json').read_text())
gh_by_key={}
for r in gh_records['records']:
 if r['metadata']:
  key='github:'+r['metadata']['nameWithOwner'].lower()
  old=gh_by_key.setdefault(key,{'response_hashes':[],'discovery_routes':[]})
  old['response_hashes']=sorted(set(old['response_hashes']+[r['response_sha256']]))
  old['discovery_routes']=sorted(set(old['discovery_routes']+r['discovery_sources']))

def write_csv(name,rows,fields):
 with (dest/f'{name}-{stamp}.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)

rankings=[{'ranking':route,**r,'packages':';'.join(r['packages'])} for route,rows in d['cohorts'].items() for r in rows]
write_csv('rankings',rankings,['ranking','rank','source_id','score','packages','first_raw_rank'])
write_csv('source-annotations',[{k:(';'.join(a[k]) if k=='evidence_urls' else a[k]) for k in ['source_id','source_type','primary_domain','manual_topic','scope_note','evidence_urls']} for a in anns],['source_id','source_type','primary_domain','manual_topic','scope_note','evidence_urls'])
observations=[]
for r in d['sources']:
 key=r['source_id'];g=r['github'];record={k:r[k] for k in ['source_id','name','source_url','summary','evidence_urls']}
 record['github']=None if not g else {'name':g['nameWithOwner'],'url':g['url'],'stars':g['stargazerCount'],'archived':g['isArchived'],'fork':g['isFork'],'head':g['defaultBranchRef']['target']['oid'] if g['defaultBranchRef'] else None,'topics':[x['topic']['name'] for x in g['repositoryTopics']['nodes']],**gh_by_key[key]}
 observations.append(record)
(dest/f'source-observations-{stamp}.json').write_text('[\n'+',\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in observations)+'\n]\n')
write_csv('tag-domains',[{'tag':k,'domain':v} for k,v in sorted(json.loads((root/'tag-domains.json').read_text()).items())],['tag','domain'])

# Retain every considered numeric row and explicit inclusion/exclusion decisions.
decisions=json.loads((root/'screening-decisions.json').read_text())
(dest/f'ranking-exclusions-{stamp}.json').write_text(json.dumps(decisions,indent=2)+'\n')
obs_by_route={route:{} for route in d['cohorts']}
for key,r in d['all_records'].items():
 for o in r['observations']:obs_by_route[o['route']][o['package']]={'source_id':key,'evidence_urls':';'.join(r['evidence_urls']),'source_url':r['source_url']}
for route in d['cohorts']:
 chosen={r['source_id'] for r in d['cohorts'][route]}; cutoff=d['cohorts'][route][-1]['score'];rows=[]
 if route=='bioconda':raw=[{'package':r['package'],'score':r['downloads'],'raw_rank':r['raw_rank'],'reason':r.get('exclusion','')} for r in json.loads((root/'bioconda-screen.json').read_text())['records']]
 elif route=='bioconductor':
  with (scratch/'bioconductor-scores.tsv').open() as f:
   import heapq
   raw=[{'package':r['Package'],'score':int(r['Download_score']),'raw_rank':i} for i,r in enumerate(heapq.nlargest(150,csv.DictReader(f,delimiter='\t'),key=lambda r:int(r['Download_score'])),1)]
 elif route=='pypi':raw=[{'package':r['project'],'score':int(r['downloads_30d']),'raw_rank':i,'reason':decisions['pypi_exclusions'].get(r['project'],'')} for i,r in enumerate(json.loads((root/'pypi-counts-without-mirrors.json').read_text())['data'],1)]
 else:
  unique={r['metadata']['nameWithOwner'].lower():r['metadata'] for r in gh_records['records'] if r['metadata']}
  raw=[{'package':m['nameWithOwner'],'score':m['stargazerCount'],'raw_rank':i,'reason':decisions['github_exclusions'].get(k,'')} for i,(k,m) in enumerate(sorted(unique.items(),key=lambda kv:(-kv[1]['stargazerCount'],kv[0])),1)]
 for row in raw:
  r=obs_by_route[route].get(row['package'],{})
  if row.get('reason'):status='excluded'
  elif r.get('source_id') in chosen:status='selected source'
  elif row['score']<cutoff:status='below cutoff; eligibility not exhaustively reviewed'
  else:status='unresolved'
  assert status!='unresolved',(route,row)
  rows.append({'raw_rank':row['raw_rank'],'package':row['package'],'score':row['score'],'source_id':r.get('source_id',''),'source_url':r.get('source_url',''),'status':status,'reason':row.get('reason',''),'evidence_urls':r.get('evidence_urls',''),'discovery_routes':';'.join(gh_by_key.get('github:'+row['package'].lower(),{}).get('discovery_routes',[])) if route=='github' else ''})
 write_csv('ranking-candidates-'+route,rows,['raw_rank','package','score','source_id','source_url','status','reason','evidence_urls','discovery_routes'])

# Provenance describes scope and retained numeric data; response hashes identify
# the external snapshots without committing bulky response bodies.
queries=[]
for f in sorted((root/'github-search').glob('*.provenance.json')):
 q=json.loads(f.read_text());raw=json.loads(f.with_name(f.name.replace('.provenance','')).read_text());q.update(total_matches=raw['total_count'],returned=len(raw['items']),last_returned_stars=raw['items'][-1]['stargazers_count'] if raw['items'] else None,incomplete_results=raw['incomplete_results']);queries.append(q)
parts=[]
for f in sorted(root.glob('pypi-metadata-part-*.provenance.json')):
 part=json.loads(f.read_text());part['sql']=f.with_name(f.name.replace('.provenance.json','.sql')).read_text();parts.append(part)
alias=json.loads((root/'pypi-metadata-aliases.provenance.json').read_text());alias['sql']=(root/'pypi-metadata-aliases.sql').read_text();parts.append(alias)
manifest={
 'date':stamp,'original_95_inventory_sha256':'e2cda0e700c76e37f28e619462cdbf5d2c7a81609af0c389fea49064fbe91c65',
 'analysis_status':'Exploratory source discovery; no package execution or task authoring; assistant manual annotations are not independently human-validated.',
 'source_identity':'Canonical upstream repository from package metadata or verified official source archive. Packaging-only distributions map upstream; independently maintained bindings and forks remain distinct. Use maximum package score per source within each registry, not the sum.',
 'bioconda':{'definition':'Cumulative nonnegative file counters across versions, builds and platforms for main-label conda artifacts.','table_url':'https://raw.githubusercontent.com/bioconda/bioconda-stats/cd491b0a4c9a7e80069c8894fbd369d8b07ceddc/package-downloads/anaconda.org/bioconda/packages.tsv','raw_table_sha256':hashlib.sha256((scratch/'bioconda-packages.tsv').read_bytes()).hexdigest(),'raw_table_rows':12740,'screened_raw_rows':250,'recipe_revision':'254ba2d4bcda7fe6ed2baa586bac6c35885a4b10','conda_forge_recipe_exceptions':json.loads((scratch/'conda-forge-recipes.json').read_text()),'cutoff':d['cohorts']['bioconda'][-1]},
 'bioconductor':{'definition':'Average monthly distinct IPs, September 2025 through August 2026; data as of September 28, 2026.','stats_url':'https://bioconductor.org/packages/stats/','table_sha256':hashlib.sha256((scratch/'bioconductor-scores.tsv').read_bytes()).hexdigest(),'table_rows':3118,'screened_raw_rows':150,'release':'3.23','metadata_url':'https://bioconductor.org/packages/3.23/bioc/VIEWS','metadata_sha256':hashlib.sha256((scratch/'bioconductor-VIEWS').read_bytes()).hexdigest(),'cutoff':d['cohorts']['bioconductor'][-1]},
 'pypi':{**json.loads((root/'pypi-counts-without-mirrors.provenance.json').read_text()),'provider':'ClickPy public ClickHouse dataset, sourced from PyPI downloads','metadata_candidate_count':15053,'returned_ranked_packages':1000,'current_pypi_identity_checks':200,'metadata_queries':parts,'count_sql_file':f'pypi-count-query-{stamp}.sql','cutoff':d['cohorts']['pypi'][-1],'provider_caveat':'Not identical to the PyPIStats snapshot used for the original 95; do not splice the counters or interpret the difference as growth. Window begins after the August 24, 2026 PyPI artifact-only download-definition change.'},
 'github':{'definition':'Current stargazerCount among the observed, screened source universe; not an exhaustive global biology ranking.','observed_at':gh_records['observed_at'],'identity_update_at':gh_records['identity_update_at'],'search_expansion_at':gh_records['search_expansion_at'],'requested_names':len(gh_records['records']),'resolved_names':sum(r['metadata'] is not None for r in gh_records['records']),'unique_resolved_repositories':len(gh_by_key),'search_queries':queries,'manual_known_source_checks':['google-deepmind/alphafold','google-deepmind/alphafold3'],'supplemental_routes':['Original 95 GitHub mappings','Bioconda top 250 recipe links','Bioconductor top 150 package links','PyPI top 1000 metadata links','Manual source identity corrections for selected packages'],'cutoff':d['cohorts']['github'][-1]},
 'manual_annotation_axes':{'source_type':'Main deliverable; embedded tutorials do not turn a software repository into a course.','primary_domain':'One primary domain per source for counting. General biology and computing infrastructure are explicit catch-all categories.','manual_topic':'Finer scientific use, assigned from metadata and selected README inspection.','scope_note':'Ambiguous or cross-domain scope and identity decisions.'},
 'source_identity_corrections':{'sortmerna':'Recipe missing at pinned revision; verified official SortMeRNA repository and build documentation.','pyopenms':'Use OpenMS/OpenMS source-code link, not the separate pyopenms-docs documentation repository.','rdkit and rdkit-pypi':'Collapse upstream and packaging distribution to rdkit/rdkit, taking maximum counter.','openbabel-wheel':'Packaging-only distribution maps to OpenBabel upstream.','mdtraj':'Current upstream mdtraj/mdtraj, rather than the legacy rmcgibbo/mdtraj project metadata link.','sssom':'README identifies mapping-commons/sssom-py despite empty project_urls.','biom-format':'README identifies biocore/biom-format despite homepage-only metadata.','vina':'README source installation points to ccsb-scripps/AutoDock-Vina.','descriptastorus':'Correct malformed https://github/ URL after verifying bp-kelley/descriptastorus.','gprofiler-official':'Use current official PyPI source distribution; no GitHub mapping asserted.','GenomeInfoDbData':'Species/taxonomy annotation-data package; official release page identifies the versioned 1.2.15 source archive. Retain distinct identity from GenomeInfoDb; no payload download or Git repository asserted.'}
}
(dest/f'pypi-count-query-{stamp}.sql').write_text((root/'pypi-counts-without-mirrors.sql').read_text())
manifest['retained_artifact_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dest.glob(f'*-{stamp}.*')) if f.name.startswith(('ranking','source-','tag-domains','pypi-count-query')) and 'results' not in f.name and 'provenance' not in f.name and 'topic-frequencies' not in f.name}
(dest/f'ranking-provenance-{stamp}.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Exported',len(rankings),'ranking rows,',len(observations),'sources')
for f in dest.glob(f'*-{stamp}.*'):
 if f.name in manifest['retained_artifact_sha256']:print(f.name,f.stat().st_size)
