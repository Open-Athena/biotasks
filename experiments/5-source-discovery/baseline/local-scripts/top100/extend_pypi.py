import datetime,hashlib,json
from pathlib import Path
import urllib.error,urllib.parse,urllib.request
root=Path('/tmp/bio-discovery-20260929/top100')
terms=['chemoinformatics','bioimaging','biomedical','biophys','anatomical','cellular','fluorescen','genome','phylogeny','electrophysiol','neurophysiol','immunolog','cytomet','crystallograph','ribonucle','deoxyribonucle']
query="""SELECT lower(replaceRegexpAll(name, '[-_.]+', '-')) AS project,
argMax(tuple(summary, keywords, classifiers, home_page, project_urls), upload_time) AS metadata,
max(upload_time) AS metadata_uploaded_at
FROM pypi.projects
WHERE multiSearchAnyCaseInsensitive(concat(name, ' ', summary, ' ', keywords), TERMS)
GROUP BY project LIMIT 9999 FORMAT JSON""".replace('TERMS',repr(terms))
(root/'pypi-metadata-aliases.sql').write_text(query+'\n')
path=root/'pypi-metadata-aliases.json'
if not path.exists():
    url='https://sql-clickhouse.clickhouse.com?'+urllib.parse.urlencode({'user':'demo','max_execution_time':30,'max_threads':1,'max_memory_usage':400_000_000,'max_block_size':1024,'preferred_block_size_bytes':1000000})
    req=urllib.request.Request(url,data=query.encode(),headers={'User-Agent':'Marin-BioTasks-discovery/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=45) as r:raw=r.read(15_000_001)
    except urllib.error.HTTPError as e:
        print(e.read().decode(),flush=True)
        raise
    data=json.loads(raw)
    assert not data.get('exception'),data.get('exception')
    assert len(data['data'])<9999
    path.write_bytes(raw)
    (root/'pypi-metadata-aliases.provenance.json').write_text(json.dumps({'terms':terms,'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'response_sha256':hashlib.sha256(raw).hexdigest(),'endpoint':url},indent=2)+'\n')
rows={}
for part in list(root.glob('pypi-metadata-part-?.json'))+[path]:
    data=json.loads(part.read_text())
    assert not data.get('exception'),data.get('exception')
    for row in data['data']:
        key=row['project']
        if key not in rows or row['metadata_uploaded_at']>rows[key]['metadata_uploaded_at']:
            rows[key]=row
(root/'pypi-metadata-search.json').write_text(json.dumps({'data':list(rows.values()),'rows':len(rows),'source_partitions':7},indent=2)+'\n')
print('Expanded PyPI metadata scope:',len(rows),flush=True)
