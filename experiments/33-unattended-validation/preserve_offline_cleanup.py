"""Append-only preservation of the already verified #34 cleanup receipt."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from preserve_followup_evidence import BUCKET, ROOT, SECRET, inspect_archive, publish, sha

SCOPE = 'issue34_owned_cleanup_metadata_only'


def prepare(source):
    manifest_path = ROOT / 'offline-cleanup-evidence-manifest.json'
    staging = ROOT / 'private/offline-cleanup-snapshot'
    assert not manifest_path.exists() and not staging.exists()
    account = json.loads((source / 'macs-742-image-cleanup-accounting.json').read_text())
    readback = json.loads((source / 'macs-742-image-cleanup-readback-001.json').read_text())
    assert account['state'] == 'succeeded' and account['exit_code'] == 0
    assert readback['result']['verified_empty'] and readback['result']['tools_removed']
    archive = source / 'inputs-private/macs-742-image-cleanup-001/outputs.tar.zst'
    assert sha(archive) == account['output_archive']['sha256'] == readback['archive_sha256']
    review = ROOT / 'offline-cleanup-public-review.json'
    assert json.loads(review.read_text())['approved_scope'] == SCOPE
    files = []
    for name, path in [
        ('evidence/cleanup.tar.zst', archive),
        ('accounting/cleanup.json', source / 'macs-742-image-cleanup-accounting.json'),
        ('provenance/readback.json', source / 'macs-742-image-cleanup-readback-001.json'),
        ('source-notices/BioTasks-LICENSE', ROOT.parents[1] / 'LICENSE'),
        ('public-eligibility-review.json', review),
    ]:
        raw = path.read_bytes()
        assert len(raw) < 1024**2 and not path.is_symlink()
        row = dict(path=name, bytes=len(raw), sha256=sha(path))
        if name.endswith('.tar.zst'):
            row.update(archive_format='tar.zst', members=inspect_archive(raw, 'tar.zst'))
            assert {m['path'] for m in row['members']} == {'cleanup-result.json'}
        else:
            raw.decode('utf-8')
            assert not SECRET.search(raw)
        dest = staging / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        files.append(row)
    manifest = dict(schema_version=1, issue=33, source_issue=34, bucket=BUCKET, visibility='public',
        source_research_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(),
        created_utc=datetime.now(timezone.utc).isoformat(), retention='Retain while cited; no automatic deletion.',
        scope='Owned cleanup output archive and verified accounting only; no task source, data or image bytes.', files=files)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(objects=len(files)+1, bytes=sum(f['bytes'] for f in files))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.source
        prepare(args.source)
    else:
        publish('offline-cleanup', SCOPE)
