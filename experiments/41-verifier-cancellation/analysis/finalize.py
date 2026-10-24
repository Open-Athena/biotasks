"""Summarize infrastructure evidence separately from historical biological trials."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import archive_tree, sha, write
from artifact_policy import inspect
import preserve

DIRECTORY = ROOT / 'private/final-summary-archive'


def summarize():
    directory = ROOT / 'private/harbor_timeout'
    receipt = preserve.verified_receipt(directory)
    complete = json.loads((directory / 'complete.json').read_text())
    assert complete['hf_manifest_sha256'] == receipt['manifest_sha256']
    read = json.loads((directory / 'readback.json').read_text())
    proof = json.loads((directory / 'cleanup-proof.json').read_text())
    assert proof['cleanup'].get('verified_empty') or proof['cleanup'].get('verified_no_creation')
    allowance = json.loads((ROOT / 'retry-allowance.json').read_text())
    results = dict(issue=41, kind=read['kind'], run_id=read['run_id'],
        finite_control_passed=read['finite_control_passed'], native_timeout_observed=read['native_timeout_observed'],
        fixture_mechanism_observed=read['fixture_mechanism_observed'], historical_scanpy_cause_proven=False,
        cases=read['cases'], native_source_parity=read['native_source_parity'],
        stage=read['stage'], error_type=read['error_type'], error_phase=read['error_phase'],
        shared_public_base_preserved=read['shared_public_base_preserved'],
        allocated_cpu_hours=read['allocated_cpu_hours'],
        prior_attempt_cpu_hours=allowance['prior_actual_cpu_hours'],
        total_main_cpu_hours=read['allocated_cpu_hours'] + allowance['prior_actual_cpu_hours'],
        raw_archive_sha256=read['archive_sha256'], hf_prefix=receipt['prefix'],
        anonymous_download_verified=True, cleanup_verified=True, cleanup_route=proof['route'],
        original_tasks_changed=False, new_biological_tasks=0, model_calls=0)
    assert results['total_main_cpu_hours'] <= 1
    write(ROOT / 'results.json', results)
    lines = ['# Native verifier cancellation diagnostic', '',
        f"Finite control passed: `{read['finite_control_passed']}`; native timeout observed: `{read['native_timeout_observed']}`; fixture mechanism observed: `{read['fixture_mechanism_observed']}`.", '',
        '| Case | Native trial exception | Starts / ends | Live prior writers | In-container hole samples | Final NUL bytes |',
        '| --- | --- | --- | --- | --- | --- |']
    for case in read['cases']:
        values = [case['name'], (case['exception'] or {}).get('exception_type'),
            str(case['writer_starts']) + ' / ' + str(case['writer_ends']), len(case['live_prior_writers']),
            case['in_container_hole_samples'], case['raw_log_nul_bytes']]
        lines.append('| ' + ' | '.join(str(v) for v in values) + ' |')
    lines += ['',
        'This is a self-authored infrastructure fixture through unchanged Harbor 0.6.6, not a biological control rerun, task export or solver score. Five-second verifier deadlines deliberately expose native cancellation/retry behavior; finite and timeout writers run for two and thirty seconds respectively. The trial must both establish its finite control and preserve independent resource/process observations before the mechanism is counted.', '',
        'Historical Scanpy causation remains unproven. Its missing rewards, old NUL holes, dependency failures and task validity are separate questions. PID/start-time identity, non-zombie state, matching log inode, independently reset offset and in-container hole samples are required here; missing events alone are not survival proof.', '',
        f"Prior preparation attempts used {allowance['prior_actual_cpu_hours']:.9f} CPU-hours; this attempt used {read['allocated_cpu_hours']:.9f}. Total main allocation {results['total_main_cpu_hours']:.9f} / 1 CPU-hour. The constructor failure and Compose rejection are separately archived, not negative mechanism results. Zero model calls/new paid capacity. Raw evidence, anonymous HF readback and owned cleanup are verified; keep issue open for user review.", '',
        f"Runtime snapshot: `hf://buckets/open-athena/biotasks/{receipt['prefix']}`.", '']
    (ROOT / 'results.md').write_text('\n'.join(lines))
    records = ROOT / 'runs/harbor_timeout'
    for path in directory.glob('*.json'):
        if path.name not in {'publication-intent.json'}:
            shutil.copyfile(path, records / path.name)
    print(json.dumps({k: results[k] for k in ['finite_control_passed', 'native_timeout_observed', 'fixture_mechanism_observed', 'total_main_cpu_hours']}))


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['issue'] == 41 and manifest['kind'] == 'completed_diagnostic_summary'
    assert manifest['public_eligible'] and {r['path'] for r in manifest['files']} == {'evidence/final-summary.tar.gz', 'public-review.json'}
    for row in manifest['files']:
        path = directory / 'snapshot' / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        assert inspect(path.read_bytes(), row.get('archive_format')) == row.get('members')
    return manifest


def prepare():
    if (DIRECTORY / 'manifest.json').exists():
        return verify(DIRECTORY)
    preserve.verified_receipt(ROOT / 'private/harbor_timeout')
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
    write(tree / 'artifact-policy-source-pointer.json', dict(commit=revision, path='experiments/41-verifier-cancellation/artifact_policy.py', sha256=sha(ROOT / 'artifact_policy.py'), reason='Scanner source contains its own prohibited literal strings; preserved exactly in Git.'))
    snapshot = DIRECTORY / 'snapshot'
    (snapshot / 'evidence').mkdir(parents=True)
    archive_tree(tree, snapshot / 'evidence/final-summary.tar.gz')
    review = dict(issue=41, public_eligible=True, scope='Diagnostic source, synthetic fixture metadata, native process measurements, accounting and provenance. No installed environments, images, package binaries, credentials or biological data.',
        inputs=inputs, results_sha256=sha(ROOT / 'results.json'), source_commit=revision, model_calls=0)
    write(snapshot / 'public-review.json', review)
    files = []
    for name, kind in [('evidence/final-summary.tar.gz', 'tar.gz'), ('public-review.json', None)]:
        path = snapshot / name
        row = dict(path=name, bytes=path.stat().st_size, sha256=sha(path), members=inspect(path.read_bytes(), kind))
        if kind:
            row['archive_format'] = kind
        files.append(row)
    write(DIRECTORY / 'manifest.json', dict(issue=41, kind='completed_diagnostic_summary', public_eligible=True,
        bucket=preserve.BUCKET, visibility='public', created_utc=datetime.now(timezone.utc).isoformat(),
        source_commit=revision, retention='Retain while cited; no automatic deletion.', files=files))
    return verify(DIRECTORY)


if __name__ == '__main__':
    if sys.argv[1] == 'summarize':
        summarize()
    elif sys.argv[1] == 'prepare':
        manifest = prepare()
        print(json.dumps(dict(manifest_sha256=sha(DIRECTORY / 'manifest.json'), files=len(manifest['files']))))
    elif sys.argv[1] == 'publish':
        print(json.dumps(preserve.publish(DIRECTORY, verifier=verify)))
    else:
        raise ValueError(sys.argv[1])
