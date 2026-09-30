import datetime, hashlib, json
from pathlib import Path
import urllib.error, urllib.parse, urllib.request
root=Path('/tmp/bio-discovery-20260929/top100')
rows=json.loads((root/'pypi-metadata-search.json').read_text())['data']
projects=[r['project'] for r in rows]
assert all("'" not in x and '\\' not in x for x in projects)
query="""SELECT project, sum(count) AS downloads_30d
FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
WHERE project IN PROJECTS
AND installer NOT IN ('bandersnatch','z3c.pypimirror','Artifactory','devpi')
AND date >= '2026-08-30' AND date <= '2026-09-28'
GROUP BY project
ORDER BY downloads_30d DESC, project ASC
LIMIT 1000
FORMAT JSON""".replace('PROJECTS','('+','.join(repr(p) for p in projects)+')')
(root/'pypi-counts-without-mirrors.sql').write_text(query+'\n')
path=root/'pypi-counts-without-mirrors.json'
if not path.exists():
    url='https://sql-clickhouse.clickhouse.com?'+urllib.parse.urlencode({'user':'demo','max_query_size':1_000_000,'max_execution_time':30,'max_threads':1,'max_memory_usage':400_000_000,'max_block_size':1024,'preferred_block_size_bytes':1000000})
    req=urllib.request.Request(url,data=query.encode(),headers={'User-Agent':'Marin-BioTasks-discovery/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=45) as r: raw=r.read(5_000_001)
    except urllib.error.HTTPError as e:
        print(e.read().decode(),flush=True)
        raise
    assert len(raw)<=5_000_000
    data=json.loads(raw)
    assert not data.get('exception'),data.get('exception')
    path.write_bytes(raw)
    (root/'pypi-counts-without-mirrors.provenance.json').write_text(json.dumps({'endpoint':url,'query_file':'pypi-counts-without-mirrors.sql','observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'response_sha256':hashlib.sha256(raw).hexdigest(),'mirror_policy':'Exclude installer values bandersnatch, z3c.pypimirror, Artifactory, and devpi, matching the PyPIStats definition.','window_start':'2026-08-30','window_end':'2026-09-28'},indent=2)+'\n')
data=json.loads(path.read_text())
meta={r['project']:r for r in rows}
print('Ranked metadata candidates:',len(data['data']),flush=True)
for i,r in enumerate(data['data'][:155],1):
    print(i,r['project'],r['downloads_30d'],meta[r['project']]['metadata'][0][:140],flush=True)
