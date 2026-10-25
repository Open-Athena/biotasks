"""Bounded normal gh metadata/source-notice reads; no repository code imports."""
import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

BASE=Path(__file__).resolve().parent
REPO='nipy/nibabel'

def save(path,obj):
    path.write_text(json.dumps(obj,indent=2)+'\n')

def get(path):
    raw=subprocess.check_output(['gh','api',path],timeout=30)
    assert len(raw)<2*1024**2
    return json.loads(raw)

def blob(path,ref):
    info=get(f'repos/{REPO}/contents/{path}?ref={ref}')
    data=base64.b64decode(info['content'])
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==info['sha']
    return info,data


def main():
    listing=json.loads((BASE/'candidates.json').read_text())
    assert len(listing['candidates'])==1
    ledger=BASE.parents[2]/'33/experiments/33-unattended-validation/task-execution-ledger.json'
    old=json.loads(ledger.read_text())
    assert all(not x['task'].lower().startswith('nipy__nibabel-') for x in old['tasks'])
    save(BASE/'dedup-preflight.json',dict(prior_ledger_sha256=hashlib.sha256(ledger.read_bytes()).hexdigest(),candidate_prs=[x['number'] for x in listing['candidates']],repository_absent_from_recorded_task_ledger=True,not_an_all_GitHub_novelty_claim=True,new_model_jobs=0))
    notices=BASE/'notices'; notices.mkdir(); target=notices/'nibabel';target.mkdir()
    shutil.copytree(BASE.parents[2]/'57/experiments/57-fresh-biopython/notices/repo2rlenv',notices/'repo2rlenv')
    config=json.loads((BASE/'native-config.json').read_text()); refs={config['repo']['ref']}; rows=[]; headers=[]
    save(BASE/'repository-metadata.json',get(f'repos/{REPO}'))
    for pr in listing['candidates']:
        num=pr['number']; meta=get(f'repos/{REPO}/pulls/{num}'); files=get(f'repos/{REPO}/pulls/{num}/files?per_page=100'); assert len(files)<100
        assert meta['base']['sha']==pr['base_sha'] and meta['head']['sha']==pr['head_sha']
        assert {x['filename'] for x in files}==set(pr['changed_files'])
        assert all(x['filename'].endswith(('.py','.rst','.md')) for x in files), 'Non-source changed files require separate review'
        save(BASE/f'pr{num}-metadata.json',meta); save(BASE/f'pr{num}-files.json',files)
        for side in ['base','head']:
            ref=meta[side]['sha'];refs.add(ref)
            for item in files:
                if item['status']=='added' and side=='base':continue
                info,data=blob(item['filename'],ref)
                header=b''.join(data.splitlines(keepends=True)[:60]); name=f"{num}-{side}-"+item['filename'].replace('/','_')+'.txt'; (target/name).write_bytes(header)
                headers.append(dict(pr=num,side=side,ref=ref,path=item['filename'],git_blob=info['sha'],source_sha256=hashlib.sha256(data).hexdigest(),notice='nibabel/'+name))
    for ref in sorted(refs):
        for name in ['COPYING']:
            info,data=blob(name,ref); filename=ref+'-'+name; (target/filename).write_bytes(data)
            assert b'The MIT License' in data and b'Philips PAR/REC data' in data and b'PDDL' in data
            rows.append(dict(ref=ref,path=name,git_blob=info['sha'],sha256=hashlib.sha256(data).hexdigest(),notice='nibabel/'+filename))
    save(notices/'SOURCE.json',dict(repo=config['repo'],license_blobs=rows,file_headers=headers,scope='Complete pinned NiBabel COPYING with MIT and third-party/data terms, changed-source headers and upstream notices; bounded text task/cache/native observations only; no environment/image or biological dataset redistribution'))
    print(json.dumps(dict(candidate_prs=[x['number'] for x in listing['candidates']],pinned_refs=len(refs),headers=len(headers),new_model_jobs=0)))

if __name__=='__main__':main()
