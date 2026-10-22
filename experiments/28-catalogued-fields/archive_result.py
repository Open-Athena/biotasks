"""Publish only a reviewed evidence allowlist, then verify fresh anonymous readback."""

import argparse
import gzip
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import datetime

from huggingface_hub import HfApi
from huggingface_hub.utils import disable_progress_bars

ROOT = Path(__file__).resolve().parent
BUCKET = 'open-athena/biotasks'
SECRET = re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}')


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def members(path, *, scan=False):
    rows = []
    total = 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            if member.isdir():
                continue
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            total += member.size
            assert member.size < 128 * 1024**2 and total < 512 * 1024**2
            with archive.extractfile(member) as handle:
                if scan:
                    raw = handle.read(16 * 1024**2 + 1)
                    assert len(raw) <= 16 * 1024**2, member.name
                    digest = hashlib.sha256(raw).hexdigest()
                    if member.name.endswith('.gz'):
                        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as decoded:
                            data = decoded.read(16 * 1024**2 + 1)
                    else:
                        data = raw
                    assert len(data) <= 16 * 1024**2 and not SECRET.search(data), member.name
                else:
                    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
            rows.append({'path': member.name, 'bytes': member.size,
                         'mode': oct(member.mode & 0o7777), 'sha256': digest})
    return rows


def main():
    disable_progress_bars()
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    cohort = json.loads((ROOT / 'cohort.json').read_text())
    row = next(r for r in cohort if r['slug'] == args.slug)
    run = 'biotasks28-' + args.slug.lower().replace('__', '-') + '-001'
    record = json.loads((args.state_dir / (run + '-terminal.json')).read_text())
    assert record['readback_verified'] and record['billing']['cost_complete']
    assert record['supervisor']['cleanup']['verified_empty']
    review_path = ROOT / 'publication-reviews' / (args.slug + '.json')
    review = json.loads(review_path.read_text())
    assert review['repo'] == row['repo'] and review['public_eligible']
    source = args.state_dir / (run + '-results')
    sources = {'evidence/' + name: source / name for name in review['reviewed_files']}
    sources['public-eligibility-review.json'] = review_path
    sources['native-config.json'] = ROOT / 'native-configs' / (args.slug + '.json')
    sources['pins.json'] = ROOT / 'pins.json'
    sources['input-checkpoint.json'] = ROOT / 'input-checkpoint.json'
    for path in sorted((ROOT / 'preflight/licenses').glob(args.slug + '--*')):
        sources['source-notices/' + path.name] = path
    sources['source-notices/Repo2RLEnv-LICENSE'] = ROOT / 'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
    files = []
    for name, path in sources.items():
        assert path.is_file()
        item = {'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
        if path.name == 'phase-artifacts.tar.gz':
            item['archive_format'] = 'tar.gz'
            item['members'] = members(path, scan=True)
        else:
            assert path.stat().st_size < 16 * 1024**2 and not SECRET.search(path.read_bytes()), path.name
        files.append(item)
    # Native jobs never include credentials in this allowlist. Whole-key billing snapshots are excluded.
    target = ROOT / 'archives'
    target.mkdir(exist_ok=True)
    manifest_path = target / (args.slug + '-manifest.json')
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert manifest['files'] == files, 'Original manifest inputs changed'
    else:
        manifest = {'schema_version': 1, 'issue': 28, 'repo': row['repo'], 'ref': row['ref'],
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'native_input_checkpoint': json.loads((ROOT / 'input-checkpoint.json').read_text())['checkpoint_commit'],
            'publication_tool_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'stage': 'original_official_pipeline_attempt_and_independent_controls',
            'retention': 'Retain while referenced; no automatic deletion.', 'files': files}
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    digest = sha(manifest_path)
    prefix = 'research/28-catalogued-fields/2026-10-22/' + digest
    api = HfApi()
    attempt = args.state_dir / (run + '-publication-attempt.json')
    prior = list(api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True))
    if prior:
        assert attempt.exists() and json.loads(attempt.read_text())['prefix'] == prefix, 'Unowned existing prefix'
    else:
        attempt.write_text(json.dumps({'prefix': prefix, 'manifest_sha256': digest}, indent=2) + '\n')
    expected = {'manifest.json': manifest_path, **sources}
    known = {f.path for f in prior if f.type == 'file'}
    assert known <= {prefix + '/' + name for name in expected}, 'Unexpected objects; do not overwrite'
    scratch = args.state_dir / (run + '-anonymous-readback')
    scratch.mkdir(exist_ok=True)
    for name, path in expected.items():
        remote = prefix + '/' + name
        if remote not in known:
            api.batch_bucket_files(BUCKET, add=[(str(path), remote)])
        # Each verification is a fresh, anonymous download, including objects from a resumed upload.
        destination = scratch / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.unlink(missing_ok=True)
        api.download_bucket_files(BUCKET, [(remote, destination)], raise_on_missing_files=True, token=False)
        assert destination.stat().st_size == path.stat().st_size and sha(destination) == sha(path)
        if path.name == 'phase-artifacts.tar.gz':
            assert members(destination) == next(f['members'] for f in files if f['path'] == name)
    receipt = {'bucket': BUCKET, 'prefix': prefix, 'manifest_sha256': digest,
               'anonymous_download_verified': True, 'verified_objects': len(expected),
               'verified_archive_members': sum(len(f.get('members', [])) for f in files),
               'client': 'huggingface_hub ' + importlib.metadata.version('huggingface_hub'),
               'method': 'Add-only missing objects; fresh anonymous object SHA256/size and archive-member SHA256/mode checks; one transfer at a time.',
               'overwrite': False, 'retention': manifest['retention']}
    (target / (args.slug + '-receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    shutil.rmtree(scratch)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
