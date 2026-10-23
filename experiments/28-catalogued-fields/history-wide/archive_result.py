"""Publish reviewed original history evidence; no account snapshots, rewrites or task changes."""

import argparse
import datetime
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from retention import PUBLIC_BUCKET, route, verified_receipt

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline_archive', BASE / 'archive_result.py')
baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'publish', 'verify'])
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    profile_path = ROOT / 'archive-client-profile.json'
    os.environ.update(read(profile_path)['environment'])
    os.environ['HF_XET_CACHE'] = str(args.state_dir / 'archive-client-cache')
    selected = next(r for r in read(BASE / 'cohort.json') if r['slug'] == args.slug)
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    terminal = read(args.state_dir / (run + '-terminal.json'))
    assert terminal['readback_verified'] and terminal['billing']['cost_complete']
    assert terminal['supervisor']['cleanup']['verified_empty']
    source = args.state_dir / (run + '-results')
    review_path = ROOT / 'publication-reviews' / (args.slug + '.json')
    review = read(review_path); assert review['repo'] == selected['repo']
    if review.get('archive_kind') == 'curated_public_with_local_originals':
        assert args.slug == 'matchms__matchms'
        from curated_matchms import run
        run(args.action, args.state_dir)
        return
    bucket, visibility = route(review)
    sources = {}
    for name in review['reviewed_files']:
        assert name == Path(name).name and name not in ['provider-usage-before.json', 'provider-usage-after.json', 'outputs.tar.zst']
        sources['evidence/' + name] = source / name
    sources.update({'public-eligibility-review.json': review_path,
        'native-config.json': ROOT / 'native-configs' / (args.slug + '.json'),
        'history-protocol.md': ROOT / 'execution-protocol.md',
        'reference-payload-manifest.json': ROOT / 'payload-manifest.json',
        'candidate-identities.json': ROOT / 'candidate-identities' / (args.slug + '.json')})
    if visibility == 'private':
        sources.update({'restricted-retention-addendum.md': ROOT / 'restricted-retention-addendum.md',
            'source-data-review.json': ROOT / 'publication-reviews' / (args.slug + '-data-review.json'),
            'private-bucket-visibility-proof.json': ROOT / 'restricted-retention-bucket.json'})
    provenance_path = ROOT / 'submission-provenance' / (args.slug + '.json')
    sources['submission-provenance.json'] = provenance_path
    for path in (BASE / 'preflight/licenses').glob(args.slug + '--*'):
        sources['source-notices/' + path.name] = path
    for relative in review.get('additional_source_notices', []):
        relative_path = Path(relative)
        assert not relative_path.is_absolute() and '..' not in relative_path.parts
        assert relative_path.parts[0] == args.slug
        path = ROOT / 'source-notices' / relative_path
        assert path.is_file() and path.resolve().is_relative_to((ROOT / 'source-notices').resolve())
        sources['source-notices/history/' + relative] = path
    sources['source-notices/Repo2RLEnv-LICENSE'] = BASE / 'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
    archive_dir = ROOT / 'archives'; archive_dir.mkdir(exist_ok=True)
    manifest_path = archive_dir / (args.slug + '-manifest.json')
    if args.action == 'prepare':
        assert not manifest_path.exists(), 'Original manifest already exists; do not replace it'
        files = []
        for name, path in sources.items():
            assert path.is_file()
            item = {'path': name, 'bytes': path.stat().st_size, 'sha256': baseline.sha(path)}
            if path.name == 'phase-artifacts.tar.gz':
                item.update(archive_format='tar.gz', members=baseline.members(path, scan=True))
            else:
                assert path.stat().st_size < 16 * 1024**2 and not baseline.SECRET.search(path.read_bytes())
            files.append(item)
        manifest = {'issue': 28, 'stage': 'history_wide_official_core_with_checkpointed_discovery_budget_orchestration',
            'repo': selected['repo'], 'ref': selected['ref'],
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'publication_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'archive_client_resource_profile_sha256': baseline.sha(profile_path),
            'archive_bucket': bucket, 'archive_visibility': visibility,
            'native_execution_checkpoint': read(provenance_path)['source_checkpoint'],
            'retention': 'Retain while referenced; no automatic deletion.', 'files': files}
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps({'repo': selected['repo'], 'objects': len(files) + 1,
            'original_phase_members': sum(len(f.get('members', [])) for f in files), 'manifest_sha256': baseline.sha(manifest_path)}))
        return
    manifest = read(manifest_path); digest = baseline.sha(manifest_path)
    assert manifest.get('archive_bucket', PUBLIC_BUCKET) == bucket
    assert manifest.get('archive_visibility', 'public') == visibility
    if 'archive_client_resource_profile_sha256' in manifest:
        assert manifest['archive_client_resource_profile_sha256'] == baseline.sha(profile_path)
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(manifest_path)], capture_output=True, check=True)
    subprocess.run(['git', 'diff', '--exit-code', '--', str(manifest_path)], capture_output=True, check=True)
    capture_date = manifest['created_utc'][:10]
    prefix = 'research/28-catalogued-fields/' + capture_date + '/' + digest
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    from huggingface_hub.errors import HfHubHTTPError
    disable_progress_bars(); api = HfApi()
    def privacy_check():
        assert api.bucket_info(bucket).private is True
        try:
            api.bucket_info(bucket, token=False)
        except HfHubHTTPError as error:
            status = error.response.status_code
            assert status in [401, 403, 404]
            return status
        raise AssertionError('Anonymous access to restricted bucket succeeded')
    if visibility == 'private':
        privacy_check()
    prior = list(api.list_bucket_tree(bucket, prefix=prefix, recursive=True))
    attempt_path = args.state_dir / (run + '-publication-attempt.json')
    if args.action == 'verify':
        assert prior, 'Read-only verification cannot create an archive'
    if prior:
        assert attempt_path.exists() and read(attempt_path)['prefix'] == prefix
        assert read(attempt_path).get('bucket', PUBLIC_BUCKET) == bucket
    else:
        attempt_path.write_text(json.dumps({'prefix': prefix, 'bucket': bucket, 'manifest_sha256': digest}, indent=2) + '\n')
    objects = {'manifest.json': manifest_path, **sources}
    known = {f.path for f in prior if f.type == 'file'}
    assert known <= {prefix + '/' + name for name in objects}
    if args.action == 'verify':
        assert known == {prefix + '/' + name for name in objects}, 'Read-only verification cannot add missing objects'
        previous = read(archive_dir / (args.slug + '-receipt.json'))
        assert previous['manifest_sha256'] == digest and verified_receipt(previous, manifest)
    with TemporaryDirectory(prefix='history-anonymous-', dir=args.state_dir) as temporary:
        if args.action == 'verify':
            # The documented BucketFile input avoids a metadata POST per object.
            # One bounded download group retains the pinned single-file stream.
            by_path = {f.path: f for f in prior if f.type == 'file'}
            downloads = []
            for name in objects:
                destination = Path(temporary) / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                downloads.append((by_path[prefix + '/' + name], destination))
            api.download_bucket_files(bucket, downloads, raise_on_missing_files=True,
                token=False if visibility == 'public' else None)
        for name, path in objects.items():
            if name != 'manifest.json':
                original = next(r for r in manifest['files'] if r['path'] == name)
                assert original['sha256'] == baseline.sha(path) and original['bytes'] == path.stat().st_size
            remote = prefix + '/' + name
            if remote not in known:
                assert args.action == 'publish'
                api.batch_bucket_files(bucket, add=[(str(path), remote)])
            destination = Path(temporary) / name; destination.parent.mkdir(parents=True, exist_ok=True)
            if args.action != 'verify':
                api.download_bucket_files(bucket, [(remote, destination)], raise_on_missing_files=True,
                    token=False if visibility == 'public' else None)
            assert destination.stat().st_size == path.stat().st_size and baseline.sha(destination) == baseline.sha(path)
            if path.name == 'phase-artifacts.tar.gz':
                assert baseline.members(destination) == next(r['members'] for r in manifest['files'] if r['path'] == name)
            destination.unlink()
    receipt = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'bucket': bucket,
        'prefix': prefix, 'manifest_sha256': digest, 'visibility': visibility,
        'anonymous_download_verified': visibility == 'public',
        'authenticated_download_verified': visibility == 'private',
        'verified_objects': len(objects), 'verified_archive_members': sum(len(f.get('members', [])) for f in manifest['files']),
        'overwrites': False, 'temporary_readbacks_removed': True, 'retention': manifest['retention'],
        'publication_tool_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'archive_client_resource_profile_sha256': baseline.sha(profile_path),
        'xet_client': 'hf_xet ' + importlib.metadata.version('hf_xet'),
        'client': 'huggingface_hub ' + importlib.metadata.version('huggingface_hub')}
    if visibility == 'private':
        receipt.update(bucket_private_verified=True, anonymous_access_denied=True,
            anonymous_http_status=privacy_check())
    assert verified_receipt(receipt, manifest)
    if args.action == 'verify':
        receipt.update(read_only_fresh_verification=True,
            verification_source_sha256=baseline.sha(Path(__file__)))
    suffix = '-fresh-readback.json' if args.action == 'verify' else '-receipt.json'
    (archive_dir / (args.slug + suffix)).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
