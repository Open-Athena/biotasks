import csv,datetime,hashlib,heapq,json,re
from pathlib import Path
import urllib.error,urllib.request
root=Path('/tmp/bio-discovery-20260929')
out=root/'top200'
rev='254ba2d4bcda7fe6ed2baa586bac6c35885a4b10'
with (root/'bioconda-packages.tsv').open() as f:
    rows=heapq.nlargest(500,csv.DictReader(f,delimiter='\t'),key=lambda r:int(r['total']))
records=[]
for rank,row in enumerate(rows,1):
    package=row['package']
    record={'package':package,'raw_rank':rank,'downloads':int(row['total'])}
    if (package.startswith('perl-') and not package.startswith('perl-bio')) or package in ['libdeflate','aria2','k8','parallel']:
        record['exclusion']='General-purpose computing dependency; no biology-specific functionality in package scope.'
        records.append(record)
        continue
    if package.startswith('bioconductor-'):
        record['bioconductor_name_hint']=package.removeprefix('bioconductor-')
        records.append(record)
        continue
    recipe_package='snakemake' if package=='snakemake-minimal' else package
    path=root/'recipes'/f'{recipe_package}.yaml'
    url=f'https://raw.githubusercontent.com/bioconda/bioconda-recipes/{rev}/recipes/{recipe_package}/meta.yaml'
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'Marin-BioTasks-discovery/1.0'})
        try:
            with urllib.request.urlopen(req,timeout=25) as resp: payload=resp.read(1_000_001)
        except urllib.error.HTTPError as e:
            if e.code != 404: raise
            record['recipe_error']=404
            records.append(record)
            print('recipe missing',package,flush=True)
            continue
        assert len(payload)<1_000_000
        path.write_bytes(payload)
        print('recipe',package,flush=True)
    content=path.read_text()
    variables=dict(re.findall(r'{% set (\w+) = ["\']([^"\']+)["\'] %}',content))
    fields={key:value.strip('"\'') for key,value in re.findall(r'^  (home|dev_url|doc_url|summary|license):\s*(.+)$',content,re.M)}
    for key in fields:
        for variable,value in variables.items(): fields[key]=fields[key].replace('{{ '+variable+' }}',value)
    record.update(fields)
    record['recipe_url']=url
    record['recipe_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    record['source_github_links']=list(dict.fromkeys(re.findall(r'https?://github.com/([\w.-]+/[\w.-]+)',content)))
    records.append(record)
(out/'bioconda-screen.json').write_text(json.dumps({'revision':rev,'raw_package_count':500,'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'records':records},indent=2)+'\n')
print('Recorded',len(records),'Bioconda package rows',flush=True)
