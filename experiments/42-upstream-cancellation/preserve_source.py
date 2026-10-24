"""Reviewed public-source snapshot, append-only upload and anonymous readback."""
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from common import archive_tree,safe,sha,write

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'private/archive';BUCKET='open-athena/biotasks'
SECRET=re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')


def inspect(raw,archive=False):
    assert len(raw)<8*1024**2
    if not archive:
        raw.decode('utf-8');assert b'\0' not in raw and not SECRET.search(raw)
        assert b'GIT binary patch' not in raw and b'data:image/' not in raw
        return None
    rows=[];seen=set();size=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as source:
        for member in source:
            safe(member.name)
            if member.isdir():continue
            assert member.isfile() and member.name not in seen and member.size<1024**2
            seen.add(member.name);size+=member.size;assert size<8*1024**2
            value=source.extractfile(member).read();inspect(value)
            import hashlib
            rows.append(dict(path=member.name,bytes=len(value),sha256=hashlib.sha256(value).hexdigest()))
    return rows


def verify():
    manifest=json.loads((ROOT/'evidence-manifest.json').read_text())
    assert manifest['issue']==42 and manifest['public_eligible'] and manifest['upstream_executed'] is False
    assert {r['path'] for r in manifest['files']}=={'evidence/source-assessment.tar.gz','public-review.json'}
    for row in manifest['files']:
        path=DEST/'snapshot'/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        assert inspect(path.read_bytes(),row.get('archive',False))==row['members']
    return manifest


def prepare():
    if (ROOT/'evidence-manifest.json').exists():return verify()
    assert not DEST.exists();tree=DEST/'tree';tree.mkdir(parents=True)
    sources=[p for p in (ROOT/'inputs-private').rglob('*') if p.is_file() and p.suffix!='.whl']
    sources+=list(ROOT.glob('*.json'))+list(ROOT.glob('*.md'))+[p for p in ROOT.glob('*.py') if p.name!='preserve_source.py']
    inputs=[]
    for source in sorted(sources):
        name=str(source.relative_to(ROOT));raw=source.read_bytes();inspect(raw)
        dest=tree/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        inputs.append(dict(path=name,bytes=len(raw),sha256=sha(source)))
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    write(tree/'publication-helper-source-pointer.json',dict(commit=revision,path='experiments/42-upstream-cancellation/preserve_source.py',sha256=sha(Path(__file__)),reason='Guard source contains prohibited literal strings; exact source is preserved in Git.'))
    snapshot=DEST/'snapshot';(snapshot/'evidence').mkdir(parents=True)
    archive_tree(tree,snapshot/'evidence/source-assessment.tar.gz')
    write(snapshot/'public-review.json',dict(issue=42,public_eligible=True,scope='Canonical public Apache-2.0 upstream source/tests and notices, exact provenance and self-authored source assessment. Package binaries excluded; no installed environments, task data, credentials or native execution.',inputs=inputs,source_commit=revision,model_calls=0))
    files=[]
    for name,is_archive in [('evidence/source-assessment.tar.gz',True),('public-review.json',False)]:
        path=snapshot/name;files.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path),archive=is_archive,members=inspect(path.read_bytes(),is_archive)))
    manifest=dict(issue=42,bucket=BUCKET,visibility='public',public_eligible=True,source_commit=revision,
        created_utc=datetime.now(timezone.utc).isoformat(),retention='Retain while cited; no automatic deletion.',files=files,upstream_executed=False,model_calls=0)
    write(ROOT/'evidence-manifest.json',manifest);return verify()


def publish():
    manifest=verify();os.environ.update(json.loads((ROOT/'archive-client-profile.json').read_text())['environment'])
    os.environ['HF_XET_CACHE']=str(DEST/'transfer-cache')
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi();assert not api.bucket_info(BUCKET).private
    prefix='research/42-upstream-cancellation/'+manifest['created_utc'][:10]+'/'+sha(ROOT/'evidence-manifest.json')
    objects=[('manifest.json',ROOT/'evidence-manifest.json',None)]+[(r['path'],DEST/'snapshot'/r['path'],r) for r in manifest['files']]
    known={r.path for r in api.list_bucket_tree(BUCKET,prefix=prefix,recursive=True) if r.type=='file'}
    intent=DEST/'publication-intent.json';expected=dict(prefix=prefix,manifest_sha256=sha(ROOT/'evidence-manifest.json'))
    if intent.exists():assert json.loads(intent.read_text())==expected
    else:assert not known;write(intent,expected)
    assert known<={prefix+'/'+name for name,_,_ in objects};receipts=[]
    try:
        with tempfile.TemporaryDirectory(prefix='anonymous-readback-',dir=DEST) as temporary:
            for name,path,row in objects:
                remote=prefix+'/'+name
                if remote not in known:api.batch_bucket_files(BUCKET,add=[(str(path),remote)])
                dest=Path(temporary)/name;dest.parent.mkdir(parents=True,exist_ok=True)
                api.download_bucket_files(BUCKET,[(remote,dest)],raise_on_missing_files=True,token=False)
                assert dest.stat().st_size==path.stat().st_size and sha(dest)==sha(path)
                if row:assert inspect(dest.read_bytes(),row['archive'])==row['members']
                receipts.append(dict(path=remote,bytes=dest.stat().st_size,sha256=sha(dest)));dest.unlink()
    finally:
        cache=DEST/'transfer-cache'
        if cache.exists():shutil.rmtree(cache)
    receipt=dict(bucket=BUCKET,prefix=prefix,manifest_sha256=sha(ROOT/'evidence-manifest.json'),objects=receipts,
        anonymous_download_verified=True,overwrites=False,owned_cache_and_readbacks_removed=True,model_calls=0)
    write(ROOT/'evidence-receipt.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='objects'}))


if __name__=='__main__':
    if sys.argv[1]=='prepare':print(json.dumps(dict(files=len(prepare()['files']))))
    elif sys.argv[1]=='publish':publish()
    else:raise ValueError(sys.argv[1])
