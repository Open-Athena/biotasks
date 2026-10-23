"""Freeze reviewed #31 archives and publish them add-only with anonymous readback."""
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
STEMS = ('macs-recorded', 'macs-longcheck', 'macs-native', 'macs-image-cleanup',
         'macs-742-image', 'macs-742-native', 'macs-742-controls', 'macs-742-image-cleanup')
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
    target = ROOT / 'private/macs-snapshot'
    assert not target.exists(), 'Never overwrite prepared evidence'
    target.mkdir(parents=True, mode=0o700)
    files = []
    def stage(name, path, archive=False):
        assert path.is_file() and not path.is_symlink() and path.stat().st_size < LIMIT
        data = path.read_bytes()
        row = {'path': name, 'bytes': len(data), 'sha256': digest(data)}
        if archive:
            row['archive_format'] = 'tar.zst'
            row['members'] = inspect_archive(data, 'tar.zst')
        else:
            data.decode('utf-8')
            assert not SECRET.search(data)
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        files.append(row)
    for stem in STEMS:
        account_path = args.followup / (stem + '-accounting.json')
        account = json.loads(account_path.read_text())
        archive = args.followup / 'inputs-private' / (stem + '-001') / 'outputs.tar.zst'
        remote = account['output_archive']
        assert remote['state'] == 'uploaded' and archive.stat().st_size == remote['size_bytes'] and sha(archive) == remote['sha256']
        assert account['attempts'] == 1 and account['state'] in ('failed', 'succeeded')
        stage('evidence/' + stem + '-001.tar.zst', archive, archive=True)
        stage('accounting/' + account_path.name, account_path)
    publication = json.loads((args.baseline / 'history-wide/archives/macs3-project__MACS-manifest.json').read_text())
    public_files = {row['path']: row for row in publication['files']}
    refs = set()
    for name in ('macs-native-manifest.json', 'macs-native-742-manifest.json'):
        m = json.loads((args.followup / name).read_text())
        refs.update((m['base_sha'], m['head_sha']))
        stage('provenance/' + name, args.followup / name)
    for ref in sorted(refs):
        rel = 'macs3-project__MACS/' + ref + '--LICENSE'
        source = args.baseline / 'history-wide/source-notices' / rel
        assert sha(source) == public_files['source-notices/history/' + rel]['sha256']
        stage('source-notices/' + ref + '--MACS-LICENSE', source)
    for source_name in ('macs3-project__MACS--LICENSE', 'huggingface__Repo2RLEnv--LICENSE'):
        stage('source-notices/' + source_name, args.baseline / 'preflight/licenses' / source_name)
    for name in ('macs-742-control-results.json', 'macs-742-control-diagnosis.json',
                 'macs-742-export-manifest.json', 'campaign-accounting.json'):
        stage('provenance/' + name, args.followup / name)
    stage('provenance/pr742-boundary-review.json', ROOT / 'pr742-boundary-review.json')
    stage('public-eligibility-review.json', ROOT / 'macs-public-review.json')
    assert sum(row['bytes'] for row in files) < 2 * 1024**2
    manifest = {'schema_version': 1, 'issue': 33, 'source_issue': 31,
                'repo': 'macs3-project/MACS', 'source_research_commit': 'a78e6e218cd92d291bfb3cc1209b74815e025344',
                'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'visibility': 'public', 'bucket': BUCKET,
                'retention': 'Retain while cited; no automatic deletion.',
                'scope': 'Eight original no-model execution archives, exact source notices, accounting and attribution correction; no Docker image or task dataset release.',
                'files': files}
    path = ROOT / 'macs-evidence-manifest.json'
    assert not path.exists()
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'objects': len(files) + 1, 'bytes': sum(row['bytes'] for row in files), 'manifest_sha256': sha(path)}))


def publish():
    for name in ('macs-evidence-manifest.json', 'macs-public-review.json', 'preserve_macs_evidence.py'):
        subprocess.run(['git', 'ls-files', '--error-unmatch', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', str(ROOT / name)], cwd=ROOT, check=True, capture_output=True)
    profile = json.loads((ROOT / 'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    cache = ROOT / 'private/hf-macs-cache'
    assert not cache.exists(), 'Inspect previous owned transfer cache before reuse'
    os.environ['HF_XET_CACHE'] = str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars()
    manifest_path = ROOT / 'macs-evidence-manifest.json'
    m = json.loads(manifest_path.read_text())
    assert m['visibility'] == 'public' and m['bucket'] == BUCKET
    review = json.loads((ROOT / 'macs-public-review.json').read_text())
    assert review['public_eligible'] is True and review['approved_scope'] == 'eight_immutable_issue31_execution_archives'
    assert sha(ROOT / 'macs-public-review.json') == next(r['sha256'] for r in m['files'] if r['path'] == 'public-eligibility-review.json')
    objects = [('manifest.json', manifest_path, None)] + [(r['path'], ROOT / 'private/macs-snapshot' / r['path'], r) for r in m['files']]
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
    attempt = ROOT / 'private/macs-publication-attempt.json'
    if known:
        assert attempt.exists() and json.loads(attempt.read_text())['prefix'] == prefix
    else:
        attempt.write_text(json.dumps({'prefix': prefix, 'manifest_sha256': sha(manifest_path)}) + '\n')
    assert known <= {prefix + '/' + name for name, _, _ in objects}
    receipt_rows = []
    try:
        with tempfile.TemporaryDirectory(prefix='macs-hf-readback-', dir=ROOT / 'private') as td:
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
    (ROOT / 'macs-evidence-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
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
