import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

root=Path('/tmp/bio-discovery-20260929/top100')
terms=['bioinformatics','biology','biological','genomics','genomic','proteomics','transcriptomics','metagenomics','microbiome','phylogen','molecular','protein','neuroscience','neuroimaging','microscopy','cheminformatics','systems biology','synthetic biology','ecology','cytometry','metabolomics','mass spectrom','sequence alignment','sequencing','single-cell','single cell','nucleic','rna-seq','dna analysis']
query="""SELECT lower(replaceRegexpAll(name, '[-_.]+', '-')) AS project,
argMax(tuple(summary, keywords, classifiers, home_page, project_urls), upload_time) AS metadata,
max(upload_time) AS metadata_uploaded_at
FROM pypi.projects
WHERE has(classifiers, 'Topic :: Scientific/Engineering :: Bio-Informatics')
OR multiSearchAnyCaseInsensitive(concat(name, ' ', summary, ' ', keywords), TERMS)
GROUP BY project
LIMIT 15000
FORMAT JSON""".replace('TERMS',repr(terms))
parts=[]
for start,end in [('', 'e'),('e','j'),('j','n'),('n','s'),('s','z'),('z','~')]:
    name='pypi-metadata-part-'+(start or '0')
    part_query=query.replace('GROUP BY project', "AND lower(name) >= '"+start+"' AND lower(name) < '"+end+"'\nGROUP BY project")
    # Apply the range to both discovery clauses.
    part_query=part_query.replace("WHERE has(","WHERE (has(").replace("\nAND lower(name)",")\nAND lower(name)",1).replace('LIMIT 15000','LIMIT 9999')
    (root/(name+'.sql')).write_text(part_query+'\n')
    path=root/(name+'.json')
    if not path.exists():
        url='https://sql-clickhouse.clickhouse.com?'+urllib.parse.urlencode({'user':'demo','max_execution_time':30,'max_threads':1,'max_memory_usage':400_000_000,'max_block_size':1024,'preferred_block_size_bytes':1000000,'max_result_bytes':15_000_000,'result_overflow_mode':'throw'})
        req=urllib.request.Request(url,data=part_query.encode(),headers={'User-Agent':'Marin-BioTasks-discovery/1.0'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=45) as r: raw=r.read(15_000_001)
        except urllib.error.HTTPError as e:
            print(e.read().decode(),flush=True)
            raise
        assert len(raw)<=15_000_000
        data=json.loads(raw)
        assert not data.get('exception'),data.get('exception')
        assert len(data['data'])<9999
        path.write_bytes(raw)
        (root/(name+'.provenance.json')).write_text(json.dumps({'endpoint':url,'query_file':name+'.sql','observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'response_sha256':hashlib.sha256(raw).hexdigest(),'terms':terms},indent=2)+'\n')
    data=json.loads(path.read_text())
    assert not data.get('exception'),data.get('exception')
    parts.extend(data['data'])
    print(name, 'candidates',len(data['data']),flush=True)
assert len(parts)==len({r['project'] for r in parts})
(root/'pypi-metadata-search.json').write_text(json.dumps({'data':parts,'rows':len(parts),'source_partitions':6},indent=2)+'\n')
print('Complete metadata candidate count:',len(parts),flush=True)
