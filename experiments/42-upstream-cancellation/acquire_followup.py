"""Follow changed call paths at already pinned commits; no source execution."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent

def main():
    target=ROOT/'source-followup.json';assert not target.exists()
    initial=json.loads((ROOT/'source-acquisition.json').read_text());records=[]
    paths=['src/harbor/trial/single_step.py','src/harbor/trial/multi_step.py','src/harbor/environments/base.py',
        'src/harbor/models/trial/config.py','src/harbor/models/task/config.py','src/harbor/models/trial/paths.py']
    for record in initial['records']:
        files=[]
        for name in paths:
            url='repos/'+initial['upstream']+'/contents/'+name+'?ref='+record['commit']
            metadata=json.loads(subprocess.check_output(['gh','api',url],timeout=60));assert metadata['type']=='file' and metadata['size']<512*1024
            raw=subprocess.check_output(['gh','api',url,'-H','Accept: application/vnd.github.raw+json'],timeout=60)
            assert len(raw)==metadata['size'];raw.decode('utf-8')
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert blob==metadata['sha']
            path=ROOT/'inputs-private'/record['label']/name;assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            files.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob_sha1=blob,
                url='https://github.com/'+initial['upstream']+'/blob/'+record['commit']+'/'+name))
        records.append(dict(label=record['label'],commit=record['commit'],files=files))
    target.write_text(json.dumps(dict(issue=42,reason='Follow extracted single/multi-step execution, log callback selection and config/paths',records=records,upstream_executed=False,model_calls=0),indent=2)+'\n')
    print(json.dumps(dict(revisions=len(records),additional_files=sum(len(r['files']) for r in records),source_only=True)))

if __name__=='__main__':main()
