"""Review the exact metadata allowlist, then publish append-only with anonymous readback."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
from tempfile import TemporaryDirectory

import zstandard

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
BUCKET = 'open-athena/biotasks'
SECRET = re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}')
NODE_FIELDS = {'id', 'number', 'title', 'url', 'createdAt', 'mergedAt', 'baseRefName', 'baseRefOid', 'headRefOid'}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def archive_members(path, expected):
    members = []; total = 0
    with path.open('rb') as source, zstandard.ZstdDecompressor().stream_reader(source) as stream, tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            name = str(PurePosixPath(member.name))
            assert not name.startswith('/') and '..' not in PurePosixPath(name).parts
            if member.isdir():
                continue
            assert member.isfile() and name in expected and member.size < 16 * 1024**2
            total += member.size; assert total < 64 * 1024**2
            raw = archive.extractfile(member).read()
            assert not SECRET.search(raw)
            if '/page-' in name:
                page = json.loads(raw)
                assert set(page) == {'data'} and set(page['data']) == {'repository', 'rateLimit'}
                for row in page['data']['repository']['pullRequests']['nodes']:
                    assert set(row) == NODE_FIELDS
            elif name.endswith('/inventory.jsonl'):
                for line in raw.splitlines():
                    assert set(json.loads(line)) == NODE_FIELDS
            else:
                assert name == 'inventory-progress.json'
            members.append({'path': name, 'bytes': member.size, 'mode': oct(member.mode & 0o7777),
                'sha256': hashlib.sha256(raw).hexdigest()})
    assert {row['path'] for row in members} == expected and len(members) == len(expected) == 248
    return members


def sources(state):
    paths = {'original-inventory-output.tar.zst': state / 'inventory-output.tar.zst',
        'original-remote.log': state / 'inventory-remote.log',
        'history-counts.json': ROOT / 'history-counts.json',
        'inventory-verification.json': ROOT / 'inventory-verification.json',
        'inventory-job-provenance.json': ROOT / 'inventory-job-provenance.json',
        'public-eligibility-review.json': ROOT / 'inventory-publication-review.json'}
    for selected in read(BASE / 'cohort.json'):
        for path in (BASE / 'preflight/licenses').glob(selected['slug'] + '--*'):
            paths['source-notices/' + path.name] = path
    paths['source-notices/Repo2RLEnv-LICENSE'] = BASE / 'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'publish'])
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    verified = read(ROOT / 'inventory-verification.json'); assert verified['full_history_enumeration_complete']
    progress = read(args.state_dir / 'inventory-result/inventory-progress.json')
    expected = {'inventory-progress.json'}
    for row in progress['repositories']:
        expected.update('pages/' + p['path'] for p in row['pages'])
        expected.add('pages/' + row['inventory']['path'])
    public = sources(args.state_dir)
    manifest_path = ROOT / 'inventory-archive-manifest.json'
    if args.action == 'prepare':
        review = {'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'public_eligible': True, 'scope': 'Exact allowlist of factual public GitHub PR identifiers/dates/ref hashes/short titles and metadata query/results, original telemetry failure, independent inventory verification and source notices. No PR bodies/diffs, downloaded biological data, patient/image/sequence files or model transcripts.',
            'credential_review': 'No Authorization headers or environment values were saved. All original plaintext leaves and allowlisted supplements pass token-pattern scanning. Exclude private Iris observation/receipt files containing archive URIs and all credentials.',
            'source_terms': 'Retain source repository and upstream notices as provenance; no assertion that metadata retention relicenses source assets. Scientific field labels remain provisional repository annotations.',
            'original_archive_members': 248, 'reviewed_files': list(public),
            'originals_and_derived_separate': True, 'no_dataset_release': True}
        (ROOT / 'inventory-publication-review.json').write_text(json.dumps(review, indent=2) + '\n')
        members = archive_members(public['original-inventory-output.tar.zst'], expected)
        files = []
        for name, path in public.items():
            assert path.is_file() and path.stat().st_size < 32 * 1024**2
            if name != 'original-inventory-output.tar.zst':
                assert not SECRET.search(path.read_bytes())
            row = {'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
            if name.endswith('.tar.zst'):
                row.update(archive_format='tar.zst', members=members)
            files.append(row)
        assert sha(public['original-inventory-output.tar.zst']) == read(ROOT / 'inventory-job-provenance.json')['archive_sha256']
        manifest = {'issue': 28, 'stage': 'full_history_metadata_inventory', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_job_state': 'FAILED_after_complete_enumeration_optional_telemetry',
            'verified_unique_merged_prs': 23285, 'verified_cursor_pages': 237,
            'source_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'retention': 'Retain while referenced; no automatic deletion.', 'files': files}
        assert not manifest_path.exists(), 'Preserve an existing original manifest'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps({'reviewed_objects': len(files), 'archive_members': len(members),
            'archive_bytes': public['original-inventory-output.tar.zst'].stat().st_size, 'manifest_sha256': sha(manifest_path)}))
        return
    manifest = read(manifest_path); digest = sha(manifest_path)
    assert read(ROOT / 'inventory-publication-review.json')['public_eligible']
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(manifest_path)], capture_output=True, check=True)
    subprocess.run(['git', 'diff', '--exit-code', '--', str(manifest_path)], capture_output=True, check=True)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars(); api = HfApi()
    prefix = 'research/28-catalogued-fields/2026-10-22/' + digest
    prior = list(api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True))
    attempt = args.state_dir / 'inventory-publication-attempt.json'
    if prior:
        assert attempt.exists() and read(attempt)['prefix'] == prefix
    else:
        attempt.write_text(json.dumps({'prefix': prefix, 'manifest_sha256': digest}, indent=2) + '\n')
    objects = {'manifest.json': manifest_path, **public}
    known = {row.path for row in prior if row.type == 'file'}
    assert known <= {prefix + '/' + name for name in objects}
    with TemporaryDirectory(prefix='inventory-anonymous-', dir=args.state_dir) as temporary:
        for name, path in objects.items():
            if name != 'manifest.json':
                original = next(row for row in manifest['files'] if row['path'] == name)
                assert path.stat().st_size == original['bytes'] and sha(path) == original['sha256']
            remote = prefix + '/' + name
            if remote not in known:
                api.batch_bucket_files(BUCKET, add=[(str(path), remote)])
            destination = Path(temporary) / name; destination.parent.mkdir(parents=True, exist_ok=True)
            api.download_bucket_files(BUCKET, [(remote, destination)], raise_on_missing_files=True, token=False)
            assert destination.stat().st_size == path.stat().st_size and sha(destination) == sha(path)
            if name.endswith('.tar.zst'):
                assert archive_members(destination, expected) == next(row['members'] for row in manifest['files'] if row['path'] == name)
            destination.unlink()
    receipt = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'bucket': BUCKET, 'prefix': prefix, 'manifest_sha256': digest, 'anonymous_download_verified': True,
        'verified_objects': len(objects), 'verified_archive_members': 248, 'overwrites': False,
        'temporary_readbacks_removed': True, 'retention': manifest['retention']}
    (ROOT / 'inventory-archive-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
