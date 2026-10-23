"""Keep task identity stable while binding each recorded environment separately."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(followup):
    ledger=json.loads((ROOT/'task-file-ledger.json').read_text())
    metadata=json.loads((ROOT/'task-source-image-metadata.json').read_text())
    evidence={}
    for name,directory in [('matchms','controls-001'),('ohif','ohif-controls-001'),('scanpy','scanpy-controls-001')]:
        record=followup/f'{name}-control-results.json';data=json.loads(record.read_text())
        file=followup/'inputs-private'/directory/'bounded-builds.jsonl'
        expected=next(f for f in data['archive_members'] if f['path']=='bounded-builds.jsonl')
        assert sha(file)==expected['sha256'] and file.stat().st_size==expected['bytes']
        evidence[name]=(data,[json.loads(line) for line in file.read_text().splitlines()],expected['sha256'])
    for task in ledger['tasks']:
        meta=metadata['tasks'][task['task']]
        task['base_commit']=meta['base_commit'];task['head_commit']=meta['head_commit']
        task['source_discovery_member_sha256']=meta['discovery_member_sha256']
        original_dockerfile=next(f['sha256'] for f in task['original_task_files'] if f['path']=='environment/Dockerfile')
        for attempt in task['attempts']:
            if attempt['environment']=='original':
                builds=meta['original_runtime_builds']
                attempt['bootstrap_image_id']=meta['bootstrap_image']
            else:
                name=attempt['source'].split('/')[1].split('-')[0]
                data,rows,digest=evidence[name]
                builds=[{k:r.get(k) for k in ['image_id','dockerfile_sha256','exit_code']} for r in rows if Path(r['context']).parent.name==task['task']]
                assert builds, task['task']
                attempt['reconstruction_image_tag']=data['retained_reconstruction_image']
                attempt['runtime_build_evidence_sha256']=digest
            assert all(b['dockerfile_sha256']==original_dockerfile for b in builds)
            attempt['runtime_image_ids']=sorted({b['image_id'] for b in builds if b['exit_code']==0 and b.get('image_id')})
            attempt['image_identity_status']='recorded successful build digest' if attempt['runtime_image_ids'] else 'no original runtime build recorded; no image inferred'
            assert not attempt['positive_pair'] or attempt['runtime_image_ids']
        task['identity_status']='base/head and task content bound; runtime images attached to attempts where built'
    ledger['limits']=['Recorded image digests do not establish current image availability or deterministic reconstruction.',
        'Six original tasks have no runtime build records; explicit absence is preserved.',
        'Original and reconstructed attempts remain separate; this is not solver performance or dataset-release readiness.',
        'The #31 MACS candidate remains excluded from the original 83-export denominator.']
    ledger['identity_coverage'].update(base_and_head_revisions=83,execution_identity_join_complete=True,
        remaining='No missing identity field silently inferred; absent original builds remain explicit.')
    ledger['execution_join_sources']={'task_file_ledger_sha256':sha(ROOT/'task-file-ledger.json'),
        'task_source_image_metadata_sha256':sha(ROOT/'task-source-image-metadata.json'),
        'followup_build_records':{k:v[2] for k,v in evidence.items()}}
    (ROOT/'task-execution-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps({'tasks':len(ledger['tasks']),'attempt_slots':sum(len(t['attempts']) for t in ledger['tasks']),
        'attempt_slots_with_runtime_image':sum(bool(a['runtime_image_ids']) for t in ledger['tasks'] for a in t['attempts'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--followup',type=Path,required=True);a=p.parse_args();main(a.followup)
