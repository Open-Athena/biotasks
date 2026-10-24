"""Publish only reviewed source/derived evidence; original raw archives stay intact."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from common import archive_tree,safe,sha,write
from policy_scan import inspect

ROOT=Path(__file__).resolve().parent
DIRECTORY=ROOT/'private/assessment-snapshot'
BUCKET='open-athena/biotasks'


def verify():
    m=json.loads((ROOT/'assessment-evidence-manifest.json').read_text())
    assert m['issue']==40 and m['bucket']==BUCKET and m['visibility']=='public' and m['public_eligible']
    assert m['review_sha256']==sha(ROOT/'public-review.json')
    assert {r['path'] for r in m['files']}=={'evidence/assessment.tar.gz','source/notices.tar.gz','public-review.json'}
    for row in m['files']:
        path=DIRECTORY/safe(row['path']);assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        assert inspect(path.read_bytes(),row.get('archive_format'))==row.get('members')
    return m


def prepare():
    if (ROOT/'assessment-evidence-manifest.json').exists():return verify()
    assert not DIRECTORY.exists()
    # Source acquisition is read-only evidence, not a new comparison/run.
    assessment=json.loads((ROOT/'source-assessment.json').read_text());assert assessment['new_remote_jobs']==assessment['new_model_calls']==0
    assert assessment['strict39_transfer']=='unsupported_as_is'
    acquisition=json.loads((ROOT/'acquisition.json').read_text());assert acquisition['anonymous_download_verified']
    for row in acquisition['files']:assert sha(ROOT/row['path'])==row['sha256']
    files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md','.txt'] and p.name not in ['policy_scan.py','public-review.json'] and not p.name.startswith(('assessment-evidence-','local-cleanup','completion-audit','publication-resources'))]
    files += list((ROOT/'inputs-private/derived').iterdir())
    reviewed=[]
    for path in sorted(files):
        raw=path.read_bytes();inspect(raw)
        assert path.is_file() and not path.is_symlink() and len(raw)<1024**2
        name='derived/'+path.name if path.parent.name=='derived' else str(path.relative_to(ROOT))
        reviewed.append(dict(source=str(path.relative_to(ROOT)),path=name,bytes=len(raw),sha256=sha(path)))
    assert sum(r['bytes'] for r in reviewed)<2*1024**2
    review=dict(issue=40,public_eligible=True,scope='Source-bound Scanpy transfer assessment and original bootstrap/action metadata; original raw archives remain referenced and unchanged.',
        source_task_review_sha256='d5f48367821197ed7156b221d1fe9f7231888962152eb66ce6fff0f2ca57b067',
        source_acquisition_sha256=sha(ROOT/'acquisition.json'),source_assessment_sha256=sha(ROOT/'source-assessment.json'),inputs=reviewed,
        exclusions='No images, installed packages, biological data, credentials or raw binary/NUL logs; original raw archives remain intact at the acquisition references.',
        scanner_source=dict(sha256=sha(ROOT/'policy_scan.py'),path='policy_scan.py',note='Exact source remains on the research branch; scanner guard literals excluded from its own raw-log inspection.'),
        retention='Retain while cited; no automatic deletion.',budget='Existing $10 archival reservation; no new paid tier, capacity or model calls.')
    write(ROOT/'public-review.json',review)
    (DIRECTORY/'evidence').mkdir(mode=0o700,parents=True);(DIRECTORY/'source').mkdir()
    with tempfile.TemporaryDirectory(prefix='assessment-tree-',dir=ROOT/'private') as temporary:
        tree=Path(temporary)
        for row in reviewed:
            dest=tree/safe(row['path']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['source'],dest)
        archive_tree(tree,DIRECTORY/'evidence/assessment.tar.gz')
    shutil.copyfile(ROOT/'inputs-private/acquired/notices.tar.gz',DIRECTORY/'source/notices.tar.gz')
    shutil.copyfile(ROOT/'public-review.json',DIRECTORY/'public-review.json')
    objects=[]
    for name in ['evidence/assessment.tar.gz','source/notices.tar.gz','public-review.json']:
        path=DIRECTORY/name;kind='tar.gz' if name.endswith('.tar.gz') else None;members=inspect(path.read_bytes(),kind)
        row=dict(path=name,bytes=path.stat().st_size,sha256=sha(path))
        if kind:row.update(archive_format=kind,members=members)
        objects.append(row)
    manifest=dict(issue=40,bucket=BUCKET,visibility='public',public_eligible=True,created_utc=datetime.now(timezone.utc).isoformat(),
        source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        review_sha256=sha(ROOT/'public-review.json'),files=objects,retention=review['retention'],new_runtime=False,new_model_calls=0)
    write(ROOT/'assessment-evidence-manifest.json',manifest);return verify()


def publish():
    for name in ['preserve_evidence.py','policy_scan.py','public-review.json','assessment-evidence-manifest.json']:
        subprocess.run(['git','ls-files','--error-unmatch',str(ROOT/name)],cwd=ROOT,check=True,capture_output=True)
        subprocess.run(['git','diff','--exit-code','HEAD','--',str(ROOT/name)],cwd=ROOT,check=True,capture_output=True)
    m=verify();os.environ.update(json.loads((ROOT/'archive-client-profile.json').read_text())['environment'])
    cache=ROOT/'private/transfer-cache';os.environ['HF_XET_CACHE']=str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi();assert not api.bucket_info(BUCKET).private
    manifest=ROOT/'assessment-evidence-manifest.json';prefix='research/40-recorded-bootstrap-transfer/'+m['created_utc'][:10]+'/'+sha(manifest)
    objects=[('manifest.json',manifest,None)]+[(r['path'],DIRECTORY/r['path'],r) for r in m['files']]
    known={r.path for r in api.list_bucket_tree(BUCKET,prefix=prefix,recursive=True) if r.type=='file'}
    intent=ROOT/'private/publication-intent.json';expected=dict(prefix=prefix,manifest_sha256=sha(manifest))
    if intent.exists():assert json.loads(intent.read_text())==expected
    else:assert not known;write(intent,expected)
    assert known<={prefix+'/'+name for name,_,_ in objects}
    receipts=[]
    try:
        with tempfile.TemporaryDirectory(prefix='anonymous-readback-',dir=ROOT/'private') as temporary:
            for name,path,row in objects:
                remote=prefix+'/'+name
                if remote not in known:api.batch_bucket_files(BUCKET,add=[(str(path),remote)])
                dest=Path(temporary)/name;dest.parent.mkdir(parents=True,exist_ok=True)
                api.download_bucket_files(BUCKET,[(remote,dest)],token=False,raise_on_missing_files=True)
                assert sha(dest)==sha(path) and dest.stat().st_size==path.stat().st_size
                if row:assert inspect(dest.read_bytes(),row.get('archive_format'))==row.get('members')
                receipts.append(dict(path=remote,bytes=dest.stat().st_size,sha256=sha(dest)));dest.unlink()
    finally:
        if cache.exists():shutil.rmtree(cache)
    receipt=dict(bucket=BUCKET,prefix=prefix,manifest_sha256=sha(manifest),anonymous_download_verified=True,objects=receipts,
        overwrites=False,owned_cache_and_readbacks_removed=True,new_model_calls=0,new_remote_jobs=0)
    write(ROOT/'assessment-evidence-receipt.json',receipt);print(json.dumps(dict(prefix=prefix,objects=len(receipts),anonymous_download_verified=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','publish']);args=parser.parse_args()
    if args.action=='prepare':
        m=prepare();print(json.dumps(dict(objects=len(m['files'])+1,bytes=sum(r['bytes'] for r in m['files']),assessment_members=len(m['files'][0]['members']))))
    else:publish()
