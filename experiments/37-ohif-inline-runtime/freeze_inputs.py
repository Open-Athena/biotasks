"""Extract exactly one archived candidate; preserve original grading bytes."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tomllib

ROOT=Path(__file__).resolve().parent
TREE=ROOT.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    epic=TREE/'33/experiments/33-unattended-validation'
    source=TREE/'36/experiments/36-inline-cache-identity'
    comparison=json.loads((source/'metadata-comparison.json').read_text())
    inventory=next(v for v in comparison['variants'] if v['variant']=='candidate')['inventory']
    source_manifest=json.loads((source/'artifact-inputs.json').read_text())['candidate']
    archive=source/source_manifest['path']
    assert sha(archive)==source_manifest['sha256'] and archive.stat().st_size==source_manifest['bytes']
    assert json.loads((source/'identity-evidence-receipt.json').read_text())['anonymous_download_verified']
    ledger=json.loads((epic/'task-execution-ledger.json').read_text())
    eligible=sorted([t for t in ledger['tasks'] if t['repo']=='OHIF/Viewers' and
        any(a['environment']=='original' and a['positive_pair'] and a['clean_oracle_command'] for a in t['attempts'])],
        key=lambda t:int(t['task'].rsplit('-',1)[1]))
    original=eligible[0];task=original['task'];assert task=='OHIF__Viewers-5996'
    prefix='outputs/OHIF__Viewers/'+task+'/'
    data={}
    with tarfile.open(archive) as tar:
        for member in tar:
            if not member.name.startswith(prefix):continue
            assert member.isfile() and member.name not in data and member.size<1024**2
            raw=tar.extractfile(member).read();name=member.name.removeprefix('outputs/OHIF__Viewers/')
            spec=inventory[name]
            assert len(raw)==member.size==spec['bytes'] and member.mode==spec['mode']
            assert hashlib.sha256(raw).hexdigest()==spec['sha256']
            data[member.name]=(raw,member.mode)
    assert len(data)==10
    unchanged=0
    for spec in original['original_task_files']:
        if spec['path'] in ('environment/Dockerfile','task.toml'):continue
        raw,mode=data[prefix+spec['path']]
        assert hashlib.sha256(raw).hexdigest()==spec['sha256'] and mode==spec['mode']
        unchanged+=1
    assert unchanged==8
    config=tomllib.loads(data[prefix+'task.toml'][0].decode())
    assert config['verifier']['timeout_sec']==300
    dockerfile=data[prefix+'environment/Dockerfile'][0].decode()
    assert re.findall(r'^FROM\s+(\S+)',dockerfile,re.M)==['node:22-slim']
    dest=ROOT/'inputs-private/cold-worker-inputs.tar.gz';assert not dest.exists()
    dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with dest.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',filename='',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
        for name,(raw,mode) in sorted(data.items()):
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=mode
            tar.addfile(member,io.BytesIO(raw))
    files=[dict(path=name,bytes=len(raw),mode=oct(mode)[2:],sha256=hashlib.sha256(raw).hexdigest()) for name,(raw,mode) in sorted(data.items())]
    per_task={name.removeprefix(prefix):dict(bytes=len(raw),mode=mode,sha256=hashlib.sha256(raw).hexdigest()) for name,(raw,mode) in data.items()}
    identity=dict(schema='biotasks-task-files-v1',repo=original['repo'],task=task,
        files=[dict(path=name,**per_task[name]) for name in sorted(per_task)])
    old_attempt=next(a for a in original['attempts'] if a['environment']=='original')
    image_refs=sorted(set([old_attempt['bootstrap_image_id'],*old_attempt['runtime_image_ids'],
        re.search(r'^# Original bootstrap ref: (\S+)',dockerfile,re.M)[1]]))
    plan=dict(scope='Archived #36 lookup-only candidate; original grading and resource contract; build-first failure stop',
        repositories=[dict(repo='OHIF/Viewers',slug='OHIF__Viewers',tasks=[dict(task=task,original_files=files,
            proposed_arms_seconds=[300],base_commit=original['base_commit'],head_commit=original['head_commit'])])],
        model_calls=0,task_repairs=0)
    manifest=dict(repo=original['repo'],task=task,selection='Lowest numeric PR with positive clean original controls',
        eligible_candidates=[t['task'] for t in eligible],base_commit=original['base_commit'],head_commit=original['head_commit'],
        original_task_identity=original['task_content_identity_sha256'],
        prepared_task_identity=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        source_candidate_archive_sha256=source_manifest['sha256'],metadata_comparison_sha256=sha(source/'metadata-comparison.json'),
        archive_sha256=sha(dest),archive_bytes=dest.stat().st_size,files=files,unchanged_original_assets=8,
        metadata_contract_unchanged=True,expected_f2p=len(json.loads(data[prefix+'tests/f2p.json'][0])),
        expected_p2p=len(json.loads(data[prefix+'tests/p2p.json'][0])),public_base_ref='node:22-slim',
        original_worker_state_refs=image_refs,original_job_id='/exedev/biotasks28-history-ohif-viewers-001',
        source_ledger_sha256=sha(epic/'task-execution-ledger.json'),model_calls=0,runtime_executed=False,
        cache_included_in_runtime_package=False,prebuilt_image_included=False,
        source_variant='Pinned native inline preparation with explicit generic cache-reader candidate from #36')
    for name,value in [('cold-worker-inputs.json',manifest),('cold-worker-control-plan.json',plan)]:
        (ROOT/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['task','archive_bytes','expected_f2p','expected_p2p','unchanged_original_assets']}))


if __name__=='__main__':main()
