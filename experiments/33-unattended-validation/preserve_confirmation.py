"""Generate a snapshot for one pre-reviewed, frozen no-model MACS attempt.

The manifest is output evidence, generated after execution. Its generating code,
source family, notices, bounds and eligibility policy are checkpointed beforehand.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from preserve_followup_evidence import ROOT, BUCKET, LIMIT, SECRET, inspect_archive, publish, sha

SCOPE = 'frozen_issue34_confirmation_with_dependency_receipts'


def prepare(source):
    target = ROOT/'private/confirmation-snapshot'
    manifest_path = ROOT/'confirmation-evidence-manifest.json'
    readback = json.loads((source/'confirmation-readback.json').read_text())
    account = json.loads((source/'confirmation-accounting.json').read_text())
    assert readback['run_id'] == 'biotasks34-macs-742-confirm-001'
    archive = source/'inputs-private/confirmation-output/outputs.tar.zst'
    assert sha(archive) == readback['archive_sha256'] == account['output_archive']['sha256']
    assert readback['model_calls'] == readback['task_repairs'] == 0
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for row in manifest['files']:
            assert sha(target/row['path']) == row['sha256']
        assert next(row['sha256'] for row in manifest['files'] if row['path'] == 'evidence/confirmation.tar.zst') == sha(archive)
        return
    assert not target.exists(), 'Partial preparation requires inspection; never replace'
    review_path = ROOT/'confirmation-public-review.json'
    review = json.loads(review_path.read_text())
    assert review['public_eligible'] and review['approved_scope'] == SCOPE
    files = []
    contents = []

    def stage(name, path, archived=False):
        assert path.is_file() and not path.is_symlink() and path.stat().st_size < LIMIT
        data = path.read_bytes()
        row = dict(path=name, bytes=len(data), sha256=sha(path))
        if archived:
            row.update(archive_format='tar.zst', members=inspect_archive(data, 'tar.zst'))
        else:
            data.decode('utf-8')
            assert not SECRET.search(data)
        files.append(row)
        contents.append((name, data))

    stage('evidence/confirmation.tar.zst', archive, True)
    for name in ('confirmation-accounting.json', 'confirmation-readback.json', 'confirmation-payload-manifest.json'):
        stage('provenance/'+name, source/name)
    previous = json.loads((ROOT/'offline-evidence-manifest.json').read_text())
    for row in previous['files']:
        if row['path'].startswith('source-notices/'):
            path = ROOT/'private/offline-snapshot'/row['path']
            assert sha(path) == row['sha256']
            stage(row['path'], path)
    stage('public-eligibility-review.json', review_path)
    assert len(files) <= 16 and sum(f['bytes'] for f in files) < 4*1024**2
    manifest = dict(schema_version=1, issue=33, source_issue=34, repo='macs3-project/MACS',
        run_id=readback['run_id'], created_utc=datetime.now(timezone.utc).isoformat(),
        source_research_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(),
        visibility='public', bucket=BUCKET, retention='Retain while cited; no automatic deletion.',
        automatic_generation_policy=SCOPE, files=files)
    target.mkdir(parents=True, mode=0o700)
    for name, data in contents:
        path = target/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(objects=len(files)+1, bytes=sum(r['bytes'] for r in files))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.source
        prepare(args.source)
    else:
        publish('confirmation', SCOPE, generated_manifest=True)
