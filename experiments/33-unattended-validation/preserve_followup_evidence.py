"""Preserve reviewed non-Matchms follow-up archives with anonymous readback."""
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

ROOT = Path(__file__).resolve().parent
BUCKET = 'open-athena/biotasks'
SECRET = re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
LIMIT = 8 * 1024**2


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


def prepare(args):
    target=ROOT/'private/followup-snapshot'
    assert not target.exists()
    target.mkdir(parents=True,mode=0o700)
    files=[]
    def stage(name,path,archive=False):
        raw=path.read_bytes();assert len(raw)<LIMIT and not path.is_symlink()
        row={'path':name,'bytes':len(raw),'sha256':digest(raw)}
        if archive:
            row['archive_format']='tar.zst';row['members']=inspect_archive(raw,'tar.zst')
        else:
            raw.decode('utf-8');assert not SECRET.search(raw)
        out=target/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw);files.append(row)
    inventory=json.loads((ROOT/'followup-archive-inventory.json').read_text())
    chosen=[r for r in inventory['archives'] if r.get('structural_scan')=='passed bounded text/archive scan']
    assert len(chosen)==13 and all('matchms' not in r['job_id'] for r in chosen)
    for row in chosen:
        folder='29-runtime-limits' if row['issue']==29 else '32-runner-coverage'
        base=args.followup/str(row['issue'])/'experiments'/folder
        source=base/row['local_relative_path']
        assert sha(source)==row['sha256'] and source.stat().st_size==row['bytes']
        stage('evidence/'+str(row['issue'])+'/'+row['accounting'].replace('-accounting.json','.tar.zst'),source,True)
        stage('accounting/'+str(row['issue'])+'/'+row['accounting'],base/row['accounting'])
    taskmeta=json.loads((ROOT/'task-source-image-metadata.json').read_text())['tasks']
    plan=json.loads((args.followup/'29/experiments/29-runtime-limits/control-plan.json').read_text())
    selected={t['task'] for r in plan['repositories'] if r['slug']!='matchms__matchms' for t in r['tasks']}
    refs={taskmeta[t][k] for t in selected for k in ('base_commit','head_commit')}
    noticed=set()
    for slug in ('OHIF__Viewers','scverse__scanpy','OpenMS__OpenMS','mne-tools__mne-python'):
        previous=args.baseline/'history-wide/archives'/(slug+'-manifest.json')
        manifest=json.loads(previous.read_text())
        stage('provenance/'+slug+'-prior-public-review.json',args.baseline/'history-wide/publication-reviews'/(slug+'.json'))
        for row in manifest['files']:
            name=row['path']
            if not name.startswith('source-notices/'):continue
            if name.startswith('source-notices/history/'):
                ref=Path(name).name.split('--')[0]
                if ref not in refs:continue
                source=args.baseline/'history-wide/source-notices'/name.removeprefix('source-notices/history/')
                noticed.add(ref)
            else:
                source_name=name.removeprefix('source-notices/')
                if source_name=='Repo2RLEnv-LICENSE':source_name='huggingface__Repo2RLEnv--LICENSE'
                source=args.baseline/'preflight/licenses'/source_name
            assert sha(source)==row['sha256']
            if name not in {r['path'] for r in files}:stage(name,source)
    assert refs<=noticed
    stage('public-eligibility-review.json',ROOT/'followup-public-review.json')
    stage('provenance/followup-archive-inventory.json',ROOT/'followup-archive-inventory.json')
    assert sum(r['bytes'] for r in files)<2*1024**2
    manifest={'schema_version':1,'issue':33,'source_issues':[29,32],
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'visibility':'public','bucket':BUCKET,'retention':'Retain while cited; no automatic deletion.',
        'scope':'Thirteen non-Matchms original execution archives, notices and accounting; no image or dataset release.',
        'files':files}
    path=ROOT/'followup-evidence-manifest.json';assert not path.exists()
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'objects':len(files)+1,'bytes':sum(r['bytes'] for r in files),'manifest_sha256':sha(path)}))


def publish():
    for name in ('followup-evidence-manifest.json', 'followup-public-review.json', 'preserve_followup_evidence.py'):
        subprocess.run(['git', 'ls-files', '--error-unmatch', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
    profile = json.loads((ROOT / 'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    cache = ROOT / 'private/hf-followup-cache'
    assert not cache.exists(), 'Inspect previous owned transfer cache before reuse'
    os.environ['HF_XET_CACHE'] = str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
    manifest_path = ROOT / 'followup-evidence-manifest.json'
    m = json.loads(manifest_path.read_text())
    assert m['visibility'] == 'public' and m['bucket'] == BUCKET
    review = json.loads((ROOT / 'followup-public-review.json').read_text())
    assert review['public_eligible'] is True and review['approved_scope'] == 'thirteen_non_matchms_followup_execution_archives'
    assert sha(ROOT / 'followup-public-review.json') == next(r['sha256'] for r in m['files'] if r['path'] == 'public-eligibility-review.json')
    objects = [('manifest.json', manifest_path, None)] + [(r['path'], ROOT / 'private/followup-snapshot' / r['path'], r) for r in m['files']]
    # All inputs are checked before any external mutation.
    for name, path, row in objects:
        if row:
            assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
            if 'members' in row:
                assert inspect_archive(path.read_bytes(), 'tar.zst') == row['members']
    prefix = 'research/33-unattended-validation/' + m['created_utc'][:10] + '/' + sha(manifest_path)
    api = HfApi()
    assert api.bucket_info(BUCKET).private is False
    known = {f.path for f in api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True) if f.type == 'file'}
    attempt = ROOT / 'private/followup-publication-attempt.json'
    if known:
        assert attempt.exists() and json.loads(attempt.read_text())['prefix'] == prefix
    else:
        attempt.write_text(json.dumps({'prefix': prefix, 'manifest_sha256': sha(manifest_path)}) + '\n')
    assert known <= {prefix + '/' + name for name, _, _ in objects}
    receipt_rows = []
    try:
        with tempfile.TemporaryDirectory(prefix='followup-hf-readback-', dir=ROOT / 'private') as td:
            for name, path, row in objects:
                remote = prefix + '/' + name
                if remote not in known:
                    api.batch_bucket_files(BUCKET, add=[(str(path), remote)])
                dest = Path(td) / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                api.download_bucket_files(BUCKET, [(remote, dest)], raise_on_missing_files=True, token=False)
                assert dest.stat().st_size == path.stat().st_size and sha(dest) == sha(path)
                if row and 'members' in row:
                    assert inspect_archive(dest.read_bytes(), 'tar.zst') == row['members']
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
    (ROOT / 'followup-evidence-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'objects'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--followup', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.baseline and args.followup
        prepare(args)
    else:
        publish()
