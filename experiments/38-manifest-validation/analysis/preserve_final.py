"""Seal reviewed summary metadata; frozen runtime publishers remain unchanged."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import archive_tree,safe,sha,write
from preserve import BUCKET,inspect,verified_receipt

REVIEW=ROOT/'analysis/final-public-review.json'
MANIFEST=ROOT/'final-evidence-manifest.json'
DIRECTORY=ROOT/'private/final-snapshot'


def checkpoint():
    for path in [Path(__file__).resolve(),REVIEW]:
        subprocess.run(['git','ls-files','--error-unmatch',str(path)],cwd=ROOT,check=True,capture_output=True)
        subprocess.run(['git','diff','--exit-code','HEAD','--',str(path)],cwd=ROOT,check=True,capture_output=True)


def verify():
    review=json.loads(REVIEW.read_text());m=json.loads(MANIFEST.read_text())
    assert review['public_eligible'] and m['review_sha256']==sha(REVIEW)
    assert m['visibility']=='public' and m['bucket']==BUCKET and m['issue']==38
    assert m['scope']=='Completed frozen-export summary and source provenance'
    assert {r['path'] for r in m['files']}=={'evidence/final-summary.tar.gz','public-eligibility-review.json'}
    assert sum(r['bytes'] for r in m['files'])<4*1024**2
    for row in m['files']:
        p=DIRECTORY/safe(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
        assert inspect(p.read_bytes(),row.get('archive_format'))==row.get('members')
    return m


def prepare():
    checkpoint()
    if MANIFEST.exists():return verify()
    assert not DIRECTORY.exists(), 'Inspect partial staging; never replace preserved evidence'
    review=json.loads(REVIEW.read_text());assert review['public_eligible'] and review['cohort_sha256']==sha(ROOT/'cohort.json')
    assert review['source_results_sha256']==sha(ROOT/'results.json')
    for family in ['opencobra__cobrapy','scverse__scanpy']:verified_receipt(ROOT/'private'/family)
    for row in review['inputs']:
        source=ROOT/safe(row['source']);assert source.is_file() and not source.is_symlink()
        assert source.stat().st_size==row['bytes'] and sha(source)==row['sha256']
        inspect(source.read_bytes(),row.get('archive_format'))
    with tempfile.TemporaryDirectory(prefix='final-summary-tree-',dir=ROOT/'private') as td:
        tree=Path(td)
        for row in review['inputs']:
            dest=tree/safe(row['path']);dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/row['source'],dest)
        target=DIRECTORY/'evidence/final-summary.tar.gz';target.parent.mkdir(mode=0o700,parents=True)
        archive_tree(tree,target)
    raw=target.read_bytes();members=inspect(raw,'tar.gz')
    assert {r['path']:r['sha256'] for r in members}=={r['path']:r['sha256'] for r in review['inputs']}
    copied=DIRECTORY/'public-eligibility-review.json';shutil.copyfile(REVIEW,copied)
    m=dict(schema_version=1,issue=38,scope='Completed frozen-export summary and source provenance',
        bucket=BUCKET,visibility='public',created_utc=datetime.now(timezone.utc).isoformat(),
        source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        review_sha256=sha(REVIEW),retention='Retain while cited; no automatic deletion.',
        files=[dict(path='evidence/final-summary.tar.gz',bytes=len(raw),sha256=sha(target),archive_format='tar.gz',members=members),
            dict(path='public-eligibility-review.json',bytes=copied.stat().st_size,sha256=sha(copied))])
    write(MANIFEST,m);return verify()


def publish():
    checkpoint();m=verify()
    os.environ.update(json.loads((ROOT/'archive-client-profile.json').read_text())['environment'])
    cache=ROOT/'private/final-transfer-cache';os.environ['HF_XET_CACHE']=str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi();assert not api.bucket_info(BUCKET).private
    prefix='research/38-manifest-validation/'+m['created_utc'][:10]+'/'+sha(MANIFEST)
    objects=[('manifest.json',MANIFEST,None)]+[(r['path'],DIRECTORY/r['path'],r) for r in m['files']]
    known={r.path for r in api.list_bucket_tree(BUCKET,prefix=prefix,recursive=True) if r.type=='file'}
    attempt=ROOT/'private/final-publication-intent.json';expected=dict(prefix=prefix,manifest_sha256=sha(MANIFEST))
    if attempt.exists():assert json.loads(attempt.read_text())==expected
    else:assert not known;write(attempt,expected)
    assert known<={prefix+'/'+name for name,_,_ in objects}
    receipts=[]
    try:
        with tempfile.TemporaryDirectory(prefix='final-anonymous-readback-',dir=ROOT/'private') as td:
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
    receipt=dict(bucket=BUCKET,prefix=prefix,manifest_sha256=sha(MANIFEST),anonymous_download_verified=True,
        objects=receipts,overwrites=False,owned_cache_and_readbacks_removed=True,model_calls=0,
        clients={name:importlib.metadata.version(name) for name in ['huggingface_hub','hf_xet']},retention=m['retention'])
    write(ROOT/'final-evidence-receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='objects'}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish']);a=p.parse_args()
    if a.action=='prepare':
        m=prepare();print(json.dumps(dict(objects=len(m['files'])+1,bytes=sum(r['bytes'] for r in m['files']),members=len(m['files'][0]['members']))))
    else:publish()
