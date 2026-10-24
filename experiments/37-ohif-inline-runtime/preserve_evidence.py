"""Reviewed bounded archival using the epic's established HF transfer policy."""
import argparse
import datetime
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent
BUCKET='open-athena/biotasks'
LIMIT=8*1024**2
SECRET=re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
SCOPE='frozen_issue37_native_inline_build_failure'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def inspect_archive(data, kind, depth=0):
    assert depth <= 3 and len(data) <= LIMIT
    if kind == 'tar.zst':
        import zstandard
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data)) as stream:
            expanded = stream.read(LIMIT + 1)
        assert len(expanded) <= LIMIT
        tar = tarfile.open(fileobj=io.BytesIO(expanded), mode='r:')
    else:
        tar = tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')
    rows, names, total = [], set(), 0
    with tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            if member.isdir():
                continue
            assert member.isfile() and member.name not in names
            names.add(member.name)
            total += member.size
            assert 0 <= member.size <= LIMIT and total <= LIMIT
            raw = tar.extractfile(member).read()
            assert len(raw) == member.size
            row = {'path': member.name, 'bytes': member.size, 'mode': oct(member.mode & 0o7777), 'sha256': digest(raw)}
            if member.name.endswith('.tar.gz'):
                row['members'] = inspect_archive(raw, 'tar.gz', depth + 1)
            else:
                raw.decode('utf-8')  # Reject unreviewed binary payloads.
                assert not SECRET.search(raw), 'Credential signal in ' + member.name
                assert b'GIT binary patch' not in raw and b'data:image/' not in raw
            rows.append(row)
    return rows

def publish(stem='runtime', approved_scope='frozen_issue37_native_inline_build_failure', generated_manifest=False):
    assert stem == 'runtime'
    assert not generated_manifest, 'Review and checkpoint the exact manifest before publishing'
    checkpointed = [f'{stem}-public-review.json', 'preserve_evidence.py']
    checkpointed.append(f'{stem}-evidence-manifest.json')
    for name in checkpointed:
        subprocess.run(['git', 'ls-files', '--error-unmatch', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
    profile = json.loads((ROOT / 'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    cache = ROOT / f'private/hf-{stem}-cache'
    assert not cache.exists(), 'Inspect previous owned transfer cache before reuse'
    os.environ['HF_XET_CACHE'] = str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
    manifest_path = ROOT / f'{stem}-evidence-manifest.json'
    m = json.loads(manifest_path.read_text())
    assert m['visibility'] == 'public' and m['bucket'] == BUCKET
    review = json.loads((ROOT / f'{stem}-public-review.json').read_text())
    assert review['public_eligible'] is True and review['approved_scope'] == approved_scope
    assert sha(ROOT / f'{stem}-public-review.json') == next(r['sha256'] for r in m['files'] if r['path'] == 'public-eligibility-review.json')
    objects = [('manifest.json', manifest_path, None)] + [(r['path'], ROOT / f'private/{stem}-snapshot' / r['path'], r) for r in m['files']]
    # All inputs are checked before any external mutation.
    for name, path, row in objects:
        if row:
            assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
            if 'members' in row:
                assert inspect_archive(path.read_bytes(), row['archive_format']) == row['members']
    prefix = 'research/37-ohif-inline-runtime/' + m['created_utc'][:10] + '/' + sha(manifest_path)
    api = HfApi()
    assert api.bucket_info(BUCKET).private is False
    known = {f.path for f in api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True) if f.type == 'file'}
    attempt = ROOT / f'private/{stem}-publication-attempt.json'
    if known:
        assert attempt.exists() and json.loads(attempt.read_text())['prefix'] == prefix
    else:
        attempt.write_text(json.dumps({'prefix': prefix, 'manifest_sha256': sha(manifest_path)}) + '\n')
    assert known <= {prefix + '/' + name for name, _, _ in objects}
    receipt_rows = []
    try:
        with tempfile.TemporaryDirectory(prefix=f'{stem}-hf-readback-', dir=ROOT / 'private') as td:
            for name, path, row in objects:
                remote = prefix + '/' + name
                if remote not in known:
                    api.batch_bucket_files(BUCKET, add=[(str(path), remote)])
                dest = Path(td) / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                api.download_bucket_files(BUCKET, [(remote, dest)], raise_on_missing_files=True, token=False)
                assert dest.stat().st_size == path.stat().st_size and sha(dest) == sha(path)
                if row and 'members' in row:
                    assert inspect_archive(dest.read_bytes(), row['archive_format']) == row['members']
                receipt_rows.append({'path': remote, 'bytes': dest.stat().st_size, 'sha256': sha(dest)})
                dest.unlink()
    finally:
        if cache.exists():
            shutil.rmtree(cache)
    receipt = {'bucket': BUCKET, 'prefix': prefix, 'manifest_sha256': sha(manifest_path),
               'anonymous_download_verified': True, 'verified_objects': len(receipt_rows), 'objects': receipt_rows,
               'overwrites': False, 'owned_cache_and_readbacks_removed': True, 'model_calls': 0,
               'client': {name: importlib.metadata.version(name) for name in ('huggingface_hub', 'hf_xet')},
               'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'retention': m['retention']}
    (ROOT / f'{stem}-evidence-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'objects'}))


def prepare():
    target=ROOT/'private/runtime-snapshot';manifest_path=ROOT/'runtime-evidence-manifest.json'
    assert not target.exists() and not manifest_path.exists(), 'Never overwrite a prepared snapshot'
    review=ROOT/'runtime-public-review.json';policy=json.loads(review.read_text())
    assert policy['public_eligible'] and policy['approved_scope']==SCOPE
    result=json.loads((ROOT/'runtime-readback.json').read_text())
    account=json.loads((ROOT/'cold-accounting.json').read_text())
    assert result['run_id']=='biotasks37-ohif-5996-inline-001' and result['stage']=='native_image_build_failed'
    assert result['missing_pnpm_observed'] and result['native_build_inner_exit']==127 and not result['rows']
    assert result['owned_resources_removed'] and account['output_archive']['sha256']==result['archive_sha256']
    files=[];contents=[]
    def stage(name,path,kind=None):
        raw=path.read_bytes();assert not path.is_symlink() and len(raw)<LIMIT
        row=dict(path=name,bytes=len(raw),sha256=digest(raw))
        if kind:row.update(archive_format=kind,members=inspect_archive(raw,kind))
        else:raw.decode('utf-8');assert not SECRET.search(raw)
        files.append(row);contents.append((name,raw))
    output=ROOT/'inputs-private/cold-output/outputs.tar.zst'
    assert sha(output)==result['archive_sha256']
    stage('evidence/runtime.tar.zst',output,'tar.zst')
    stage('evidence/native-task.tar.gz',ROOT/'inputs-private/cold-worker-inputs.tar.gz','tar.gz')
    stage('evidence/original-bootstrap.json',ROOT/'inputs-private/original-bootstrap.json')
    upstream=ROOT.parents[2]/'31/experiments/31-historical-builds/inputs-private/upstream-package/src/repo2rlenv/registry/integration.py'
    assessment=json.loads((ROOT/'recipe-source-assessment.json').read_text())
    assert sha(upstream)==assessment['source_file_sha256']
    stage('upstream-source/registry-integration.py',upstream)
    for name in ['cold-accounting.json','runtime-readback.json','bootstrap-provenance.json',
                 'recipe-source-assessment.json','cold-payload-manifest.json','cold-worker-inputs.json',
                 'diagnosis.md','failure-stop-check.json','worker-selector-check.json']:
        stage('provenance/'+name,ROOT/name)
    stage('provenance/epic-budget.json',ROOT.parents[2]/'33/experiments/33-unattended-validation/budget.json')
    baseline=ROOT.parents[3]/'experiments/28-catalogued-fields'
    prior=json.loads((baseline/'history-wide/archives/OHIF__Viewers-manifest.json').read_text())
    cache=json.loads((ROOT/'inputs-private/original-bootstrap.json').read_text())
    assert prior['ref']==cache['ref']
    inputs=json.loads((ROOT/'cold-worker-inputs.json').read_text())
    names=['source-notices/OHIF__Viewers--LICENSE']+[
        'source-notices/history/OHIF__Viewers/'+inputs[k]+'--LICENSE' for k in ['base_commit','head_commit']]
    for name in names:
        row=next(r for r in prior['files'] if r['path']==name)
        if '/history/' in name:path=baseline/'history-wide/source-notices'/name.removeprefix('source-notices/history/')
        else:path=baseline/'preflight/licenses'/name.removeprefix('source-notices/')
        assert sha(path)==row['sha256'];stage(name,path)
    notice=ROOT.parents[2]/'35/experiments/35-durable-runtime-artifacts/private/cold-snapshot/source-notices/Repo2RLEnv-LICENSE'
    assert sha(notice)=='c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'
    stage('source-notices/Repo2RLEnv-LICENSE',notice)
    stage('public-eligibility-review.json',review)
    assert len(files)<=24 and sum(r['bytes'] for r in files)<4*1024**2
    manifest=dict(schema_version=1,issue=37,epic=33,repo='OHIF/Viewers',
        run_id=result['run_id'],source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),visibility='public',bucket=BUCKET,
        retention='Retain while cited; no automatic deletion.',files=files)
    target.mkdir(mode=0o700,parents=True)
    for name,raw in contents:
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(objects=len(files)+1,bytes=sum(r['bytes'] for r in files))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','publish'])
    if parser.parse_args().action=='prepare':prepare()
    else:publish()

