"""Append-only preservation of the already verified #34 cleanup receipt."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from preserve_followup_evidence import BUCKET, ROOT, SECRET, inspect_archive, publish, sha

SCOPE = 'issue34_owned_cleanup_metadata_only'
FINAL_SCOPE = 'confirmation_completion_and_owned_cleanup'


def prepare(source, confirmation=False):
    stem = 'confirmation-final' if confirmation else 'offline-cleanup'
    scope = FINAL_SCOPE if confirmation else SCOPE
    accounting = 'confirmation-cleanup-accounting.json' if confirmation else 'macs-742-image-cleanup-accounting.json'
    readback_name = 'confirmation-cleanup-readback.json' if confirmation else 'macs-742-image-cleanup-readback-001.json'
    archive_dir = 'confirmation-cleanup-output' if confirmation else 'macs-742-image-cleanup-001'
    manifest_path = ROOT / f'{stem}-evidence-manifest.json'
    staging = ROOT / f'private/{stem}-snapshot'
    assert not manifest_path.exists() and not staging.exists()
    account = json.loads((source / accounting).read_text())
    readback = json.loads((source / readback_name).read_text())
    assert account['state'] == 'succeeded' and account['exit_code'] == 0
    assert readback['result']['verified_empty'] and readback['result']['tools_removed']
    archive = source / 'inputs-private' / archive_dir / 'outputs.tar.zst'
    assert sha(archive) == account['output_archive']['sha256'] == readback['archive_sha256']
    review = ROOT / f'{stem}-public-review.json'
    assert json.loads(review.read_text())['approved_scope'] == scope
    extra = []
    if confirmation:
        assert account['job_id'] == '/exedev/biotasks34-macs-742-confirm-cleanup-001'
        assert readback['result']['controls']['verified_empty']
        summary = json.loads((ROOT/'confirmation-summary.json').read_text())
        assert summary['lifecycle_complete'] and summary['new_model_calls'] == 0
        extra = [('provenance/'+name, ROOT/name) for name in ('confirmation-summary.json',
            'confirmation-restart-proof.json', 'diagnostic-task-ledger.json', 'confirmation-evidence-receipt.json', 'budget.json')]
    files = []
    for name, path in [
        ('evidence/cleanup.tar.zst', archive),
        ('accounting/cleanup.json', source / accounting),
        ('provenance/readback.json', source / readback_name),
        ('source-notices/BioTasks-LICENSE', ROOT.parents[1] / 'LICENSE'),
        ('public-eligibility-review.json', review),
    ] + extra:
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
        scope=scope, files=files)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(objects=len(files)+1, bytes=sum(f['bytes'] for f in files))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--confirmation', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.source
        prepare(args.source, args.confirmation)
    else:
        publish('confirmation-final', FINAL_SCOPE) if args.confirmation else publish('offline-cleanup', SCOPE)
