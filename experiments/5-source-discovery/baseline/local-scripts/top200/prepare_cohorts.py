import csv,heapq,json,re
from pathlib import Path
from urllib.parse import urlsplit

root=Path('/tmp/bio-discovery-20260929')
out=root/'top200'
baseline=json.loads(Path('docs/experiments/bio-task-generation/01-discovery/inventory.json').read_text())['candidates']
bioc=json.loads((root/'bioconductor-metadata.json').read_text())
bioc_names={name.lower():name for name in bioc}
decisions=json.loads((out/'screening-decisions.json').read_text())
overrides=json.loads((out/'identity-overrides.json').read_text())
github={}
requested={}
for record in json.loads((out/'github-source-metadata.json').read_text())['records']:
    m=record['metadata']
    if m:
        key=m['nameWithOwner'].lower()
        github[key]=m
        requested[record['requested_name'].lower()]=key

# Preserve metadata as observed for the original ranking pool, including topics.
github.update({r['metadata']['nameWithOwner'].lower():r['metadata'] for r in json.loads((root/'top100/github-source-metadata.json').read_text())['records'] if r['metadata']})

def github_names(text):
    return list(dict.fromkeys(s.lower().removesuffix('.git').rstrip('.') for s in re.findall(r'https?://(?:www\.)?github.com/([\w.-]+/[\w.-]+)',text or '')))

def canonical(url):
    names=github_names(url)
    if names:
        name=requested.get(names[0],names[0])
        return 'github:'+name, github[name]['url'] if name in github else 'https://github.com/'+name
    if 'GenomeInfoDbData_' in url:
        return 'bioconductor:genomeinfodbdata',url
    if 'git.bioconductor.org/packages/' in url:
        return 'bioconductor:'+url.rsplit('/',1)[1].lower(),url
    return url.lower().rstrip('/'),url

records={}
def insert(name,url,summary,evidence,route,package,score,raw_rank,details=None):
    key,url=canonical(url)
    if key not in records:
        gh=github.get(key.removeprefix('github:')) if key.startswith('github:') else None
        records[key]={'source_id':key,'name':name,'source_url':url,'summary':(gh['description'] if gh and gh['description'] else summary) or '','github':gh,'evidence_urls':[],'observations':[]}
    r=records[key]
    if evidence and evidence not in r['evidence_urls']:r['evidence_urls'].append(evidence)
    r['observations'].append({'route':route,'package':package,'score':score,'raw_rank':raw_rank,**(details or {})})
    return key

baseline_conda={p['name']:r for r in baseline for p in r['bioconda_packages']}
baseline_pypi={p['name'].lower():r for r in baseline for p in r['pypi_packages']}

def bioc_source(name):
    m=bioc.get(name,{})
    slugs=github_names(' '.join(m.get(k,'') for k in ['BugReports','URL']))
    if slugs:return 'https://github.com/'+slugs[0]
    return 'https://git.bioconductor.org/packages/'+name

with (root/'bioconductor-scores.tsv').open() as f:
    biorows=heapq.nlargest(250,csv.DictReader(f,delimiter='\t'),key=lambda r:int(r['Download_score']))
for rank,r in enumerate(biorows,1):
    name=r['Package'];m=bioc.get(name,{})
    insert(name,bioc_source(name),m.get('Title',''),f'https://bioconductor.org/packages/3.23/bioc/html/{name}.html','bioconductor',name,int(r['Download_score']),rank,{'biocViews':m.get('biocViews',''),'description':m.get('Description','')})

conda_overrides={
'sortmerna':('SortMeRNA','https://github.com/sortmerna/sortmerna','Ribosomal RNA read filtering and alignment.'),
'genometools-genometools':('GenomeTools','https://github.com/genometools/genometools','Genome analysis and annotation utilities.'),
'bioconductor-genomeinfodbdata':('GenomeInfoDbData','https://bioconductor.org/packages/release/data/annotation/src/contrib/GenomeInfoDbData_1.2.15.tar.gz','Species and taxonomy data for GenomeInfoDb.'),
'bioconductor-data-packages':('Bioconductor data-package installer','https://github.com/bioconda/bioconda-recipes','Bioconductor data-package installation support.'),
'gmap':('GMAP / GSNAP','http://research-pub.gene.com/gmap','Genomic mapping and alignment for mRNA and EST sequences.'),
}
forge={r['package']:r['url'] for r in json.loads((root/'conda-forge-recipes.json').read_text())}
for row in json.loads((out/'bioconda-screen.json').read_text())['records']:
    package=row['package']
    if package in forge:row['recipe_url']=forge[package]
    if package=='sortmerna':row['recipe_url']='https://github.com/sortmerna/sortmerna'
    if row.get('exclusion') or row.get('mapping_deferred') or package in decisions['bioconda_exclusions']:continue
    if package in overrides['bioconda']:name,url,summary=package,overrides['bioconda'][package],row.get('summary','')
    elif package in conda_overrides:name,url,summary=conda_overrides[package]
    elif package in baseline_conda:
        old=baseline_conda[package];name=old['name'];summary=old['scientific_use']
        url=bioc_source(old['bioconductor_package']) if old.get('bioconductor_package') else (old['repository_url'] or old['source_distribution']['url'])
    elif 'bioconductor_name_hint' in row:
        hint=row['bioconductor_name_hint'];name=bioc_names.get(hint,hint)
        url=bioc_source(name);summary=bioc.get(name,{}).get('Title','Bioconductor package '+name)
    elif row.get('recipe_error'):
        continue
    else:
        name=package;summary=row.get('summary','')
        home=row.get('dev_url') or row.get('home') or ''
        slugs=github_names(home)
        if not slugs:
            slugs=[s.lower().removesuffix('.git') for s in row.get('source_github_links',[]) if s.lower() not in ['bioconda/bioconda-recipes','conda/conda','bioconda/bioconda-utils','adoptopenjdk/openjdk-build']]
        url='https://github.com/'+slugs[0] if slugs else home
        if not url:raise ValueError(package)
    insert(name,url,summary,row.get('recipe_url',f'https://github.com/bioconda/bioconda-recipes/tree/254ba2d4bcda7fe6ed2baa586bac6c35885a4b10/recipes/{package}'),'bioconda',package,row['downloads'],row['raw_rank'])

pypi_overrides={'pyopenms':'https://github.com/OpenMS/OpenMS','mdtraj':'https://github.com/mdtraj/mdtraj','biom-format':'https://github.com/biocore/biom-format','sssom':'https://github.com/mapping-commons/sssom-py','descriptastorus':'https://github.com/bp-kelley/descriptastorus','vina':'https://github.com/ccsb-scripps/AutoDock-Vina','rdkit':'https://github.com/rdkit/rdkit','rdkit-pypi':'https://github.com/rdkit/rdkit','openbabel-wheel':'https://github.com/openbabel/openbabel','py3dmol':'https://github.com/3dmol/3Dmol.js'}
for rank,row in enumerate(json.loads((out/'pypi-counts-without-mirrors.json').read_text())['data'][:350],1):
    name=row['project']
    if name in decisions['pypi_exclusions']:continue
    data=json.loads((out/'pypi-current'/(name+'.json')).read_text())
    if data.get('error_status'):continue
    m=data['metadata'];urls=m.get('project_urls') or {}
    summary=m.get('summary') or ''
    if name == 'gprofiler-official':url=data['source_distributions'][0]['url']
    elif name in overrides['pypi']:url=overrides['pypi'][name]
    elif name in pypi_overrides:url=pypi_overrides[name]
    elif name in baseline_pypi:
        old=baseline_pypi[name];url=old['repository_url']
    else:
        prioritised=sorted(urls.items(),key=lambda kv:(0 if 'repository' in kv[0].lower() or ('source' in kv[0].lower() and 'documentation' not in kv[0].lower()) else 1 if 'home' in kv[0].lower() else 2))
        slugs=github_names(' '.join(v for k,v in prioritised))
        if slugs:url='https://github.com/'+slugs[0]
        else:
            url=m.get('home_page') or next(iter(urls.values()),'')
            if not url or not url.startswith('http'):
                url=data['source_distributions'][0]['url'] if data['source_distributions'] else f'https://pypi.org/project/{name}/'
    insert(name,url,summary,data['source_url'],'pypi',name,int(row['downloads_30d']),rank,{'metadata_summary':summary,'package_version':m['version']})

frozen_github={r['metadata']['nameWithOwner'].lower():r['metadata'] for r in json.loads((root/'top100/github-source-metadata.json').read_text())['records'] if r['metadata']}
ranked_github=heapq.nlargest(len(frozen_github),frozen_github.values(),key=lambda m:(m['stargazerCount'],m['nameWithOwner']))
for rank,m in enumerate(ranked_github,1):
    name=m['nameWithOwner'];key=name.lower()
    if key in decisions['github_exclusions']:continue
    insert(name,m['url'],m['description'],m['url'],'github',name,m['stargazerCount'],rank)

cohorts={}
for route in ['bioconda','bioconductor','pypi','github']:
    candidates=[]
    for key,r in records.items():
        obs=[o for o in r['observations'] if o['route']==route]
        if not obs:continue
        maximum=max(o['score'] for o in obs)
        candidates.append({'source_id':key,'score':maximum,'packages':[o['package'] for o in obs],'first_raw_rank':min(o['raw_rank'] for o in obs)})
    leaders=heapq.nsmallest(200,candidates,key=lambda r:(-r['score'],r['source_id']))
    assert len(leaders)==200,(route,len(leaders))
    cohorts[route]=[{'rank':i,**row} for i,row in enumerate(leaders,1)]
    print(route,'eligible resolved pool',len(candidates),'cutoff',leaders[-1]['score'],'last raw rank',leaders[-1]['first_raw_rank'],flush=True)
keys=set(r['source_id'] for cohort in cohorts.values() for r in cohort)
(out/'cohorts-provisional.json').write_text(json.dumps({'cohorts':cohorts,'sources':[records[k] for k in sorted(keys)],'all_records':records},indent=2)+'\n')
print('Selected union:',len(keys),flush=True)
for route in cohorts:
    print('\n'+route.upper())
    for row in cohorts[route]:
        record=records[row['source_id']]
        print(row['rank'],record['name'],row['score'],record['source_id'],record['summary'])
