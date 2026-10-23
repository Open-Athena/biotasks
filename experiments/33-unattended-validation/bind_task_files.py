"""Bind reconciled task names to retained full-phase member inventories."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':')).encode()).hexdigest()


def bind(ledger, baseline, followup):
    result=json.loads(ledger.read_text())
    sources={str(ledger.name):hashlib.sha256(ledger.read_bytes()).hexdigest()}
    manifests={}
    plan=json.loads(followup.read_text())
    sources['29/control-plan.json']=hashlib.sha256(followup.read_bytes()).hexdigest()
    selected={t['task']:t for r in plan['repositories'] for t in r['tasks']}
    identities=set()
    checked_followups=0
    def canonical(files, prefix):
        rows=[]
        for f in files:
            path=Path(f['path'])
            rel=path.relative_to(prefix)
            assert '..' not in rel.parts and not rel.is_absolute()
            rows.append(dict(path=str(rel),bytes=f['bytes'],mode=int(f['mode'],8),sha256=f['sha256']))
        assert len(rows)==len({r['path'] for r in rows})
        return sorted(rows,key=lambda r:r['path'])
    for task in result['tasks']:
        slug=task['repo'].replace('/','__')
        if slug not in manifests:
            name='drafts/matchms__matchms-unpublished-private-manifest.json' if slug=='matchms__matchms' else slug+'-manifest.json'
            path=baseline/'archives'/name
            raw=path.read_bytes();data=json.loads(raw)
            sources['28/archives/'+name]=hashlib.sha256(raw).hexdigest()
            phase=[f for f in data['files'] if f['path']=='evidence/phase-artifacts.tar.gz']
            assert len(phase)==1
            manifests[slug]=phase[0]
        phase=manifests[slug]
        assert phase['sha256']==task['original_phase_sha256']
        prefix=Path('outputs')/slug/task['task']
        files=[f for f in phase['members'] if Path(f['path']).is_relative_to(prefix)]
        rows=canonical(files,prefix)
        assert len(rows)==10, task['task']
        identity=digest({'schema':'biotasks-task-files-v1','repo':task['repo'],'task':task['task'],'files':rows})
        assert identity not in identities
        identities.add(identity)
        task['task_content_identity_sha256']=identity
        task['original_task_files']=rows
        task['identity_status']='ten-file inventory bound to original phase; explicit base/head and image digest still pending'
        if task['task'] in selected:
            assert rows==canonical(selected[task['task']]['original_files'],prefix)
            task['followup_input_inventory_matches_original']=True
            checked_followups+=1
    assert checked_followups==len(selected)
    result['limits'][0]='Full base/head and runtime image-digest reconciliation remains pending; task file identities are now bound to retained inventories.'
    result['identity_sources_sha256']=sources
    result['identity_coverage']={'tasks_with_ten_file_identity':len(identities),'followup_input_inventories_matched':checked_followups,
        'identity_schema':'SHA256 of canonical JSON: schema, repo, task, and sorted relative path/size/mode/hash rows',
        'raw_files_rehashed_this_step':False,
        'matchms_manifest_usage':'Historical full-phase inventory only; its obsolete private-bucket location is not a storage claim.',
        'remaining':'Explicit base/head source revisions and runtime image digests; no release readiness claim.'}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['ledger','baseline','followup','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=bind(a.ledger,a.baseline,a.followup)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r['identity_coverage']))
