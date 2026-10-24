"""Preserve the exact failed startup; never synthesize normal stage success."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import archive_tree, sha, write
from artifact_policy import inspect
import preserve

DEST = ROOT / 'private/failed-startup-archive'


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['issue'] == 41 and manifest['kind'] == 'adapter_startup_failure'
    assert manifest['native_fixture_executed'] is False
    assert {r['path'] for r in manifest['files']} == {'evidence/failed-startup.tar.gz', 'disposition.json'}
    for row in manifest['files']:
        path = directory / 'snapshot' / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        assert inspect(path.read_bytes(), row.get('archive_format')) == row.get('members')
    return manifest


def prepare():
    if (DEST / 'manifest.json').exists():
        return verify(DEST)
    plan = json.loads((ROOT / 'runtime-plan.json').read_text())
    family = plan['families'][0]
    assert family['run_id'] == 'biotasks41-cancel-07c39c2ac6'
    payload = ROOT / family['payload_directory']
    for name, digest in family['payload_sha256'].items():
        assert sha(payload / name) == digest
    logs = json.loads((ROOT / 'private/failed-attempt-sdk-logs.json').read_text())
    text = '\n'.join(r['data'] for r in logs['logs'])
    assert "KeyError: 'tasks'" in text and 'supervisor_base.py' in text
    assert 'line 23, in __init__' in text and 'line 100, in main' in text
    config = json.loads((payload / 'family.json').read_text())
    assert 'tasks' not in config and len(config['cases']) == 2
    parent = ast.parse((payload / 'supervisor_base.py').read_text())
    constructor = next(n for n in ast.walk(parent) if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    assert all(isinstance(n, ast.Assign) for n in constructor.body)
    assert [ast.unparse(n.func) for n in ast.walk(constructor) if isinstance(n, ast.Call)] == ['Path', 'Path', 'dict', 'dict', 'time.time']
    worker = ast.parse((payload / 'worker_job.py').read_text())
    diagnostic = next(n for n in worker.body if isinstance(n, ast.ClassDef) and n.name == 'Diagnostic')
    assert not any(isinstance(n, ast.FunctionDef) and n.name == '__init__' for n in diagnostic.body)
    main = next(n for n in worker.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    assert ast.unparse(main.body[1]).startswith('supervisor = Diagnostic(')
    assert ast.unparse(main.body[-1]) == 'supervisor.execute()'
    account = json.loads((ROOT / 'private/harbor_timeout/accounting.json').read_text())
    assert account['state'] == 'failed' and account['attempts'] == 1 and account['output_archive']['state'] == 'empty'
    proof = dict(issue=41, run_id=family['run_id'], verified_no_creation=True,
        scope='No nested task-owned Docker objects: inherited pure constructor raised before execute/validate/work. Managed Iris attempt did execute and is charged.',
        native_fixture_executed=False, biological_tasks=0, model_calls=0,
        sdk_logs_sha256=sha(ROOT / 'private/failed-attempt-sdk-logs.json'),
        payload_manifest=family['payload_manifest'], actual_accounting=account,
        normal_journal_completed=False, disposition='Archive source-bound startup failure; retain incomplete original journal. Never resume this fixed handle.',
        limitation='Empty output alone is not no-creation proof; proof also binds traceback, exact source, constructor order and config. No live daemon inventory was needed because creation code was never reached.')
    tree = DEST / 'tree'
    assert not (DEST / 'publication-intent.json').exists()
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    for name in ['runtime-plan.json', 'cohort.json', 'public-policy.json', 'pre-admission-checkpoint.json', 'probe-checks.json', 'package-acquisition.json', 'test-dependency-acquisition.json']:
        shutil.copyfile(ROOT / name, tree / name)
    for path in ROOT.glob('*.py'):
        if path.name == 'artifact_policy.py':
            write(tree / 'artifact-policy-source-pointer.json', dict(commit='2a723b3b', path=path.name, sha256=sha(path), reason='Scanner source contains its own prohibited literal strings; exact source retained in Git.'))
            continue
        (tree / 'source').mkdir(exist_ok=True)
        shutil.copyfile(path, tree / 'source' / path.name)
    shutil.copytree(ROOT / 'private/harbor_timeout', tree / 'original-incomplete-controller-state')
    for name in ['failed-attempt-sdk-logs.json', 'controller-001.log']:
        shutil.copyfile(ROOT / 'private' / name, tree / name)
    (tree / 'payload').mkdir()
    excluded = []
    for path in payload.iterdir():
        if path.suffix == '.whl':
            excluded.append(dict(path=path.name, sha256=sha(path), reason='Package binary excluded; public acquisition URL and hash retained.'))
        else:
            shutil.copyfile(path, tree / 'payload' / path.name)
    write(tree / 'excluded-package-binaries.json', excluded)
    write(tree / 'disposition.json', proof)
    snapshot = DEST / 'snapshot'
    if snapshot.exists():
        shutil.rmtree(snapshot)
    (snapshot / 'evidence').mkdir(parents=True, exist_ok=True)
    archive_tree(tree, snapshot / 'evidence/failed-startup.tar.gz')
    write(snapshot / 'disposition.json', proof)
    files = []
    for name, kind in [('evidence/failed-startup.tar.gz', 'tar.gz'), ('disposition.json', None)]:
        path = snapshot / name
        row = dict(path=name, bytes=path.stat().st_size, sha256=sha(path), members=inspect(path.read_bytes(), kind))
        if kind:
            row['archive_format'] = kind
        files.append(row)
    write(DEST / 'manifest.json', dict(issue=41, kind='adapter_startup_failure', native_fixture_executed=False,
        bucket=preserve.BUCKET, visibility='public', created_utc=datetime.now(timezone.utc).isoformat(),
        source_checkpoint='2a723b3b', original_journal_incomplete=True, files=files,
        retention='Retain while cited; no automatic deletion.', public_eligibility='Self-authored diagnostic code/configuration, synthetic fixture, SDK traceback and accounting. No package binaries, credentials, images or biological data.'))
    return verify(DEST)


if __name__ == '__main__':
    prepare()
    if '--publish' in sys.argv:
        print(json.dumps(preserve.publish(DEST, verifier=verify)))
    else:
        print(json.dumps(dict(manifest_sha256=sha(DEST / 'manifest.json'), files=len(verify(DEST)['files']))))
