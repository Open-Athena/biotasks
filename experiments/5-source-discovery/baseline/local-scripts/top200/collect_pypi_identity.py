import datetime,hashlib,json
from pathlib import Path
import urllib.error,urllib.request
root=Path('/tmp/bio-discovery-20260929/top100')
cache=root/'pypi-current'
cache.mkdir(exist_ok=True)
rows=json.loads((root/'pypi-counts-without-mirrors.json').read_text())['data'][:350]
fields=['name','version','summary','home_page','project_urls','classifiers','keywords','requires_python','license_expression']
for i,row in enumerate(rows,1):
    name=row['project']
    path=cache/(name+'.json')
    if not path.exists():
        url=f'https://pypi.org/pypi/{name}/json'
        req=urllib.request.Request(url,headers={'User-Agent':'Marin-BioTasks-discovery/1.0'})
        try:
            with urllib.request.urlopen(req,timeout=25) as response:raw=response.read(12_000_001)
        except urllib.error.HTTPError as e:
            if e.code !=404:raise
            path.write_text(json.dumps({'error_status':404,'url':url})+'\n')
            continue
        assert len(raw)<=12_000_000,(name,len(raw))
        data=json.loads(raw)
        info={key:data['info'].get(key) for key in fields}
        info['description']=data['info'].get('description','')[:20000]
        sdists=[{'url':r['url'],'sha256':r['digests']['sha256']} for r in data['urls'] if r['packagetype']=='sdist']
        record={'metadata':info,'source_distributions':sdists,'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'source_url':url,'response_sha256':hashlib.sha256(raw).hexdigest()}
        path.write_text(json.dumps(record,indent=2)+'\n')
    if i%25==0:print('Current PyPI identity',i,'/',len(rows),flush=True)
print('Current PyPI identity complete:',len(rows),flush=True)
