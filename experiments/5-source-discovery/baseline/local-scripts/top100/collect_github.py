import datetime
import hashlib
import json
from pathlib import Path
import subprocess

root=Path('/tmp/bio-discovery-20260929/top100/github-search')
root.mkdir(exist_ok=True)
terms=['bioinformatics','biology','genomics','proteomics','transcriptomics','metagenomics','microbiome','phylogenetics','molecular','protein','neuroscience','neuroimaging','microscopy','cheminformatics','systems-biology','synthetic-biology','ecology','medical-imaging','biomedical','bioimaging','single-cell','drug-discovery','structural-biology','computational-biology']
for term in terms:
    path=root/(term+'.json')
    query=f'{term} in:name,description,topics fork:false is:public stars:>=500'
    if not path.exists():
        result=subprocess.run(['gh','api','search/repositories','--method','GET','-f','q='+query,'-f','sort=stars','-f','order=desc','-F','per_page=100'],capture_output=True,timeout=45)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        data=json.loads(result.stdout)
        if data['incomplete_results']:
            raise RuntimeError('Incomplete GitHub results for '+term)
        path.write_bytes(result.stdout)
        (root/(term+'.provenance.json')).write_text(json.dumps({'query':query,'sort':'stars','order':'desc','per_page':100,'page':1,'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'sha256':hashlib.sha256(result.stdout).hexdigest()},indent=2)+'\n')
    data=json.loads(path.read_text())
    print(term, 'matches',data['total_count'],'returned',len(data['items']),'last_stars',data['items'][-1]['stargazers_count'] if data['items'] else None,flush=True)
