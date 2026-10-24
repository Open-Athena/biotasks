"""Generated, source-bound public snapshots with append-only anonymous readback."""
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from common import content_sha,safe,sha,write

ROOT=Path(__file__).resolve().parent
BUCKET='open-athena/biotasks'
LIMIT=32*1024**2
SECRET=re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')


def inspect(raw,kind=None,depth=0):
    assert len(raw)<=LIMIT and depth<=3
    if not kind:
        raw.decode('utf-8')
        assert not SECRET.search(raw) and b'GIT binary patch' not in raw and b'data:image/' not in raw
        assert b'\x00' not in raw
        return None
    if kind=='tar.zst':
        import zstandard
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as stream:expanded=stream.read(LIMIT+1)
        assert len(expanded)<=LIMIT
        archive=tarfile.open(fileobj=io.BytesIO(expanded),mode='r:')
    else:archive=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')
    rows=[];names=set();total=0
    with archive:
        for member in archive:
            safe(member.name)
            if member.isdir():continue
            assert member.isfile() and member.name not in names and 0<=member.size<8*1024**2
            names.add(member.name);total+=member.size;assert total<=LIMIT
            value=archive.extractfile(member).read();assert len(value)==member.size
            nested='tar.gz' if member.name.endswith('.tar.gz') else None
            children=inspect(value,nested,depth+1)
            row=dict(path=member.name,bytes=member.size,mode=oct(member.mode),sha256=content_sha(value))
            if children is not None:row['members']=children
            rows.append(row)
    return rows


def verify_stage(directory):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    policy=json.loads((ROOT/'public-policy.json').read_text())
    assert manifest['issue']==39 and manifest['bucket']==BUCKET and manifest['visibility']=='public'
    assert policy['public_eligible'] and manifest['policy_sha256']==sha(ROOT/'public-policy.json')
    assert manifest['source_family_sha256']==policy['source_families'][manifest['family']]
    expected={'evidence/runtime.tar.zst','provenance/submission.json','provenance/accounting.json','provenance/readback.json',
        'public-eligibility-policy.json','provenance/runtime-plan.json'}
    if manifest['cleanup']:expected|={'provenance/primary-manifest.json','provenance/primary-readback.json'}
    else:expected|={'source/native-tasks.tar.gz','source/notices.tar.gz','provenance/cohort.json',
        'provenance/candidate-preparation.json','provenance/candidate-static-findings.json','source/portable-inputs.tar.gz'}
    assert {row['path'] for row in manifest['files']}==expected and len(expected)==len(manifest['files'])
    assert sum(row['bytes'] for row in manifest['files'])<=LIMIT
    for row in manifest['files']:
        path=directory/'snapshot'/safe(row['path']);assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        assert inspect(path.read_bytes(),row.get('archive_format'))==row.get('members')
    return manifest


def prepare(family,directory,cleanup=False):
    directory=Path(directory);snapshot=directory/'snapshot';target=directory/'manifest.json'
    policy=json.loads((ROOT/'public-policy.json').read_text());assert policy['public_eligible']
    assert policy['cohort_sha256']==sha(ROOT/'cohort.json') and policy['source_families'][family['id']]==family['source_family_sha256']
    if target.exists():return verify_stage(directory)
    # Staging is reproducible scratch until the manifest exists. Never overwrite a published intent.
    assert not (directory/'publication-intent.json').exists()
    if snapshot.exists():shutil.rmtree(snapshot)
    snapshot.mkdir(mode=0o700)
    files=[]
    def add(name,path,kind=None):
        safe(name);assert path.is_file() and not path.is_symlink()
        raw=path.read_bytes();members=inspect(raw,kind)
        row=dict(path=name,bytes=len(raw),sha256=content_sha(raw))
        if kind:row.update(archive_format=kind,members=members)
        dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files.append(row)
    add('evidence/runtime.tar.zst',directory/'output/outputs.tar.zst','tar.zst')
    for name in ['submission.json','accounting.json','readback.json']:
        add('provenance/'+name,directory/name)
    add('public-eligibility-policy.json',ROOT/'public-policy.json')
    add('provenance/runtime-plan.json',ROOT/'runtime-plan.json')
    if not cleanup:
        source=json.loads((ROOT/'cohort.json').read_text())
        original=next(f for f in source['families'] if f['id']==family['id'])
        for key in ['task_bundle','notices_bundle']:
            assert sha(ROOT/original[key]['path'])==original[key]['sha256']
        add('source/native-tasks.tar.gz',ROOT/original['task_bundle']['path'],'tar.gz')
        add('source/notices.tar.gz',ROOT/original['notices_bundle']['path'],'tar.gz')
        add('provenance/cohort.json',ROOT/'cohort.json')
        add('provenance/candidate-preparation.json',ROOT/'candidate-preparation.json')
        add('source/portable-inputs.tar.gz',ROOT/'private/input-publication/snapshot/inputs.tar.gz','tar.gz')
        add('provenance/candidate-static-findings.json',ROOT/'candidate-static-findings.json')
    else:
        add('provenance/primary-manifest.json',directory.parent/'manifest.json')
        add('provenance/primary-readback.json',directory.parent/'readback.json')
    assert len(files)<=16 and sum(row['bytes'] for row in files)<=LIMIT
    manifest=dict(schema_version=1,issue=39,family=family['id'],run_id=family['run_id'],cleanup=cleanup,
        created_utc=datetime.now(timezone.utc).isoformat(),bucket=BUCKET,visibility='public',
        source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_family_sha256=family['source_family_sha256'],policy_sha256=sha(ROOT/'public-policy.json'),
        retention='Retain while cited; no automatic deletion.',files=files)
    write(target,manifest);return verify_stage(directory)


def publish(directory,verifier=verify_stage):
    directory=Path(directory);manifest=verifier(directory);manifest_path=directory/'manifest.json'
    os.environ.update(json.loads((ROOT/'archive-client-profile.json').read_text())['environment'])
    cache=directory/'hf-transfer-cache';os.environ['HF_XET_CACHE']=str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi();assert not api.bucket_info(BUCKET).private
    prefix='research/39-recorded-bootstrap/'+manifest['created_utc'][:10]+'/'+sha(manifest_path)
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
