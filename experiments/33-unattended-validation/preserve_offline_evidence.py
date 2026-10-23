"""Prepare/publish the bounded #34 reconstruction and control evidence snapshot."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from preserve_followup_evidence import BUCKET, LIMIT, ROOT, SECRET, digest, inspect_archive, publish, sha

SCOPE = 'issue34_reconstruction_and_offline_controls'


def prepare(followup, baseline):
    target = ROOT / 'private/offline-snapshot'
    manifest_path = ROOT / 'offline-evidence-manifest.json'
    assert not target.exists() and not manifest_path.exists(), 'Preserve existing snapshot; never replace'
    review_path = ROOT / 'offline-public-review.json'
    review = json.loads(review_path.read_text())
    assert review['public_eligible'] is True and review['approved_scope'] == SCOPE
    readback = json.loads((followup / 'macs-742-control-results.json').read_text())
    image = json.loads((followup / 'macs-742-image-readback-001.json').read_text())
    assert image['result_record_verified'] and readback['model_calls'] == 0
    files = []
    staged = []

    def stage(name, source, archive=False):
        assert source.is_file() and not source.is_symlink() and source.stat().st_size < LIMIT
        raw = source.read_bytes()
        row = dict(path=name, bytes=len(raw), sha256=digest(raw))
        if archive:
            row.update(archive_format='tar.zst', members=inspect_archive(raw, 'tar.zst'))
        else:
            raw.decode('utf-8')
            assert not SECRET.search(raw)
        staged.append((name, raw))
        files.append(row)

    for stem, receipt in [('macs-742-image', image), ('macs-742-controls', readback)]:
        account_path = followup / (stem + '-accounting.json')
        account = json.loads(account_path.read_text())
        assert account['state'] in ('succeeded', 'failed') and account['attempts'] == 1
        archive = followup / 'inputs-private' / (stem + '-001') / 'outputs.tar.zst'
        assert sha(archive) == account['output_archive']['sha256'] == receipt['archive_sha256']
        assert archive.stat().st_size == account['output_archive']['size_bytes']
        stage('evidence/' + stem + '-001.tar.zst', archive, True)
        stage('accounting/' + account_path.name, account_path)
    for name in ('macs-742-image-readback-001.json', 'macs-742-control-results.json',
                 'offline-control-inputs.json', 'offline-export-manifest.json',
                 'offline-control-plan.json', 'macs-base-dependency-plan.json'):
        stage('provenance/' + name, followup / name)
    previous = json.loads((baseline / 'history-wide/archives/macs3-project__MACS-manifest.json').read_text())
    published = {row['path']: row for row in previous['files']}
    for ref in ('26f6709ede9d69e7a4091c7e89fb0639006a6f8e', 'b0e3a8a28778e8f99a0cc2713e18d4be121c3922'):
        rel = 'macs3-project__MACS/' + ref + '--LICENSE'
        source = baseline / 'history-wide/source-notices' / rel
        assert sha(source) == published['source-notices/history/' + rel]['sha256']
        stage('source-notices/' + ref + '--MACS-LICENSE', source)
    for name in ('macs3-project__MACS--LICENSE', 'huggingface__Repo2RLEnv--LICENSE'):
        stage('source-notices/' + name, baseline / 'preflight/licenses' / name)
    stage('public-eligibility-review.json', review_path)
    assert sum(row['bytes'] for row in files) < 4 * 1024**2
    manifest = dict(schema_version=1, issue=33, source_issue=34, repo='macs3-project/MACS',
        source_research_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=followup, text=True).strip(),
        created_utc=datetime.now(timezone.utc).isoformat(), visibility='public', bucket=BUCKET,
        retention='Retain while cited; no automatic deletion.',
        scope='Two zero-model execution archives, unchanged task lineage, offline dependency receipt and exact source notices; no image or package-cache release.',
        files=files)
    # Write only after all source, nested archive and notice checks pass.
    target.mkdir(parents=True, mode=0o700)
    for name, raw in staged:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(objects=len(files) + 1, bytes=sum(r['bytes'] for r in files), manifest_sha256=sha(manifest_path))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--followup', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        assert args.followup and args.baseline
        prepare(args.followup, args.baseline)
    else:
        publish('offline', SCOPE)
