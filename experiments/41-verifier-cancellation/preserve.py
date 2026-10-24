"""Append-only diagnostic evidence, explicit synthetic-log eligibility only."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from artifact_policy import inspect
from common import content_sha,safe,sha,write

ROOT=Path(__file__).resolve().parent
BUCKET='open-athena/biotasks'
LIMIT=32*1024**2


def names(cleanup):
    common={'evidence/runtime.tar.zst','provenance/submission.json','provenance/accounting.json','provenance/readback.json',
        'public-eligibility-policy.json','provenance/runtime-plan.json'}
    return common|({'provenance/primary-manifest.json','provenance/primary-readback.json'} if cleanup else {
        'source/fixture-tasks.tar.gz','source/notices.tar.gz','provenance/cohort.json','provenance/package-acquisition.json',
        'provenance/test-dependency-acquisition.json','provenance/source-assessment.json','provenance/cancellation-checks.json'})


def verify_stage(directory):
    directory=Path(directory);m=json.loads((directory/'manifest.json').read_text());policy=json.loads((ROOT/'public-policy.json').read_text())
    assert m['issue']==41 and m['bucket']==BUCKET and m['visibility']=='public' and policy['public_eligible']
    assert m['policy_sha256']==sha(ROOT/'public-policy.json') and m['source_family_sha256']==policy['source_families'][m['family']]
    assert {r['path'] for r in m['files']}==names(m['cleanup']) and sum(r['bytes'] for r in m['files'])<=LIMIT
    for row in m['files']:
        path=directory/'snapshot'/safe(row['path']);assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        assert inspect(path.read_bytes(),row.get('archive_format'))==row.get('members')
    return m


def prepare(family,directory,cleanup=False):
    directory=Path(directory);target=directory/'manifest.json'
    if target.exists():return verify_stage(directory)
    assert not (directory/'publication-intent.json').exists()
    policy=json.loads((ROOT/'public-policy.json').read_text());assert policy['public_eligible'] and policy['cohort_sha256']==sha(ROOT/'cohort.json')
    assert policy['source_families'][family['id']]==family['source_family_sha256']
    snapshot=directory/'snapshot'
    if snapshot.exists():shutil.rmtree(snapshot)
    snapshot.mkdir(mode=0o700);files=[]
    def add(name,path,kind=None):
        raw=path.read_bytes();members=inspect(raw,kind);row=dict(path=name,bytes=len(raw),sha256=content_sha(raw))
        if kind:row.update(archive_format=kind,members=members)
        dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files.append(row)
    add('evidence/runtime.tar.zst',directory/'output/outputs.tar.zst','tar.zst')
    for name in ['submission.json','accounting.json','readback.json']:add('provenance/'+name,directory/name)
    add('public-eligibility-policy.json',ROOT/'public-policy.json');add('provenance/runtime-plan.json',ROOT/'runtime-plan.json')
    if cleanup:
        add('provenance/primary-manifest.json',directory.parent/'manifest.json');add('provenance/primary-readback.json',directory.parent/'readback.json')
    else:
        f=json.loads((ROOT/'cohort.json').read_text())['families'][0]
        for key,name in [('task_bundle','fixture-tasks.tar.gz'),('notices_bundle','notices.tar.gz')]:
            path=ROOT/f[key]['path'];assert sha(path)==f[key]['sha256'];add('source/'+name,path,'tar.gz')
        for name in ['cohort.json','package-acquisition.json','test-dependency-acquisition.json','source-assessment.json','cancellation-checks.json']:add('provenance/'+name,ROOT/name)
    m=dict(schema_version=1,issue=41,family=family['id'],run_id=family['run_id'],cleanup=cleanup,bucket=BUCKET,visibility='public',
        created_utc=datetime.now(timezone.utc).isoformat(),source_family_sha256=family['source_family_sha256'],policy_sha256=sha(ROOT/'public-policy.json'),
        source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        retention='Retain while cited; no automatic deletion.',files=files)
    write(target,m);return verify_stage(directory)


def publish(directory,verifier=verify_stage):
    directory=Path(directory);manifest=verifier(directory);manifest_path=directory/'manifest.json'
    os.environ.update(json.loads((ROOT/'archive-client-profile.json').read_text())['environment'])
    cache=directory/'hf-transfer-cache';os.environ['HF_XET_CACHE']=str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi();assert not api.bucket_info(BUCKET).private
    prefix='research/41-verifier-cancellation/'+manifest['created_utc'][:10]+'/'+sha(manifest_path)
    objects=[('manifest.json',manifest_path,None)]+[(r['path'],directory/'snapshot'/r['path'],r) for r in manifest['files']]
    known={f.path for f in api.list_bucket_tree(BUCKET,prefix=prefix,recursive=True) if f.type=='file'}
    intent=directory/'publication-intent.json';expected=dict(prefix=prefix,manifest_sha256=sha(manifest_path))
    if intent.exists():assert json.loads(intent.read_text())==expected
    else:assert not known;write(intent,expected)
    assert known<={prefix+'/'+name for name,_,_ in objects}
    receipts=[]
    try:
        with tempfile.TemporaryDirectory(prefix='anonymous-readback-',dir=directory) as td:
            for name,path,row in objects:
                remote=prefix+'/'+name
                if remote not in known:api.batch_bucket_files(BUCKET,add=[(str(path),remote)])
                dest=Path(td)/name;dest.parent.mkdir(parents=True,exist_ok=True)
                api.download_bucket_files(BUCKET,[(remote,dest)],raise_on_missing_files=True,token=False)
                assert dest.stat().st_size==path.stat().st_size and sha(dest)==sha(path)
                if row:assert inspect(dest.read_bytes(),row.get('archive_format'))==row.get('members')
                receipts.append(dict(path=remote,bytes=dest.stat().st_size,sha256=sha(dest)));dest.unlink()
    finally:
        if cache.exists():shutil.rmtree(cache)
    receipt=dict(bucket=BUCKET,prefix=prefix,manifest_sha256=sha(manifest_path),anonymous_download_verified=True,
        objects=receipts,overwrites=False,owned_cache_and_readbacks_removed=True,model_calls=0)
    write(directory/'hf-receipt.json',receipt);return receipt

def verified_receipt(directory):
    directory=Path(directory);m=verify_stage(directory);receipt=json.loads((directory/'hf-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(directory/'manifest.json')
    expected={'manifest.json':sha(directory/'manifest.json'),**{r['path']:r['sha256'] for r in m['files']}}
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}==expected
    return receipt
