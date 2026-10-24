"""Final summary/source archival; native code and original journal remain frozen."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import archive_tree,sha,write
from artifact_policy import inspect
import preserve
DIRECTORY=ROOT/'private/final-summary-archive'

def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['issue'] == 43 and manifest['kind'] == 'completed_diagnostic_summary'
    assert manifest['public_eligible'] and {r['path'] for r in manifest['files']} == {'evidence/final-summary.tar.gz', 'public-review.json'}
    for row in manifest['files']:
        path = directory / 'snapshot' / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        assert inspect(path.read_bytes(), row.get('archive_format')) == row.get('members')
    return manifest


def prepare():
    if (DIRECTORY / 'manifest.json').exists():
        return verify(DIRECTORY)
    preserve.verified_receipt(ROOT / 'private/harbor_comparison')
    assert not DIRECTORY.exists()
    tree = DIRECTORY / 'tree'
    tree.mkdir(parents=True)
    sources = sorted(ROOT.glob('*.json')) + sorted(ROOT.glob('*.md')) + sorted(ROOT.glob('*.sh'))
    sources += [p for p in ROOT.glob('*.py') if p.name != 'artifact_policy.py']
    sources += sorted((ROOT / 'runs').rglob('*.json'))
    sources += sorted((ROOT / 'analysis').glob('*.py'))
    inputs = []
    for source in sources:
        raw = source.read_bytes()
        inspect(raw)
        name = str(source.relative_to(ROOT))
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        inputs.append(dict(path=name, bytes=len(raw), sha256=sha(path)))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    write(tree / 'artifact-policy-source-pointer.json', dict(commit=revision, path='experiments/43-native-harbor-comparison/artifact_policy.py', sha256=sha(ROOT / 'artifact_policy.py'), reason='Scanner source contains its own prohibited literal strings; preserved exactly in Git.'))
    snapshot = DIRECTORY / 'snapshot'
    (snapshot / 'evidence').mkdir(parents=True)
    archive_tree(tree, snapshot / 'evidence/final-summary.tar.gz')
    review = dict(issue=43, public_eligible=True, scope='Diagnostic source, synthetic fixture metadata, native process measurements, accounting and provenance. No installed environments, images, package binaries, credentials or biological data.',
        inputs=inputs, results_sha256=sha(ROOT / 'results.json'), source_commit=revision, model_calls=0)
    write(snapshot / 'public-review.json', review)
    files = []
    for name, kind in [('evidence/final-summary.tar.gz', 'tar.gz'), ('public-review.json', None)]:
        path = snapshot / name
        row = dict(path=name, bytes=path.stat().st_size, sha256=sha(path), members=inspect(path.read_bytes(), kind))
        if kind:
            row['archive_format'] = kind
        files.append(row)
    write(DIRECTORY / 'manifest.json', dict(issue=43, kind='completed_diagnostic_summary', public_eligible=True,
        bucket=preserve.BUCKET, visibility='public', created_utc=datetime.now(timezone.utc).isoformat(),
        source_commit=revision, retention='Retain while cited; no automatic deletion.', files=files))
    return verify(DIRECTORY)



if __name__=='__main__':
    if sys.argv[1]=='prepare':
        manifest=prepare();print(json.dumps(dict(manifest_sha256=sha(DIRECTORY/'manifest.json'),files=len(manifest['files']))))
    elif sys.argv[1]=='publish':print(json.dumps(preserve.publish(DIRECTORY,verifier=verify)))
    else:raise ValueError(sys.argv[1])
