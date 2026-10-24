"""Freeze the first native-prepared export with original clean controls."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tomllib

from probe_native_inline import ROOT, COORDINATOR, inventory, sha, write


def identity(repo, task, files):
    value = dict(schema='biotasks-task-files-v1', repo=repo, task=task,
        files=[dict(path=name, **files[name]) for name in sorted(files)])
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    probe = json.loads((ROOT/'native-inline-probe.json').read_text())
    ledger = json.loads((COORDINATOR/'task-execution-ledger.json').read_text())
    tasks = {t['task']:t for t in ledger['tasks']}
    candidates = []
    for case in probe['cases']:
        if case['state'] != 'prepared' or case['separate_diagnostic']:
            continue
        for task in case['tasks']:
            if any(a['environment'] == 'original' and a['positive_pair'] and a['clean_oracle_command'] for a in tasks[task]['attempts']):
                candidates.append((case['repo'], int(task.rsplit('-', 1)[1]), task))
    assert candidates
    repo, _, task = sorted(candidates)[0]
    original = tasks[task]
    slug = repo.replace('/', '__')
    source = ROOT/'inputs-private/native-preparation'/slug/'prepared'/task
    before = ROOT/'inputs-private/native-preparation'/slug/'original'/task
    old_files = inventory(before)
    assert identity(repo, task, old_files) == original['task_content_identity_sha256']
    new_files = inventory(source)
    prepared_case = next(c for c in probe['cases'] if c['repo'] == repo)
    recorded = {name.removeprefix(task+'/'):spec for name,spec in prepared_case['prepared_inventory'].items() if name.startswith(task+'/')}
    assert new_files == recorded, 'Prepared bytes changed after native API verification'
    assert len(new_files) == 10
    changed = [name for name in old_files if old_files[name] != new_files[name]]
    assert set(changed) == {'environment/Dockerfile', 'task.toml'}
    config = tomllib.loads((source/'task.toml').read_text())
    assert config['verifier']['timeout_sec'] == 300
    assert config['metadata']['repo2env']['reproducibility']['mode'] == 'inline_dockerfile'
    dockerfile = (source/'environment/Dockerfile').read_text()
    references = re.findall(r'^FROM\s+(\S+)', dockerfile, re.M)
    assert len(references) == 1 and references[0] == 'python:3.12-slim'
    path = ROOT/'inputs-private/cold-worker-inputs.tar.gz'
    assert not path.exists(), 'Preserve the frozen candidate; never overwrite'
    prefix = Path('outputs')/slug/task
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode='w|') as tar:
        for name in sorted(new_files):
            item = source/name
            member = tar.gettarinfo(str(item), arcname=str(prefix/name))
            member.uid = member.gid = member.mtime = 0
            member.uname = member.gname = ''
            with item.open('rb') as stream:
                tar.addfile(member, stream)
    specs = [dict(path=str(prefix/name), bytes=row['bytes'], sha256=row['sha256'], mode=oct(row['mode'])[2:]) for name,row in sorted(new_files.items())]
    with tarfile.open(path) as tar:
        members = tar.getmembers()
        assert len(members) == 10 and {m.name for m in members} == {r['path'] for r in specs}
        for member in members:
            spec = next(r for r in specs if r['path'] == member.name)
            assert member.isfile() and member.size == spec['bytes'] and member.mode == int(spec['mode'], 8)
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == spec['sha256']
    original_from = re.search(r'^FROM\s+(\S+)', (before/'environment/Dockerfile').read_text(), re.M)[1]
    original_attempt = next(a for a in original['attempts'] if a['environment'] == 'original')
    plan = dict(scope='Unmodified native inline artifact on a different clean worker; original grading assets and settings retained.',
        repositories=[dict(repo=repo, slug=slug, tasks=[dict(task=task, original_files=specs, proposed_arms_seconds=[300],
            base_commit=original['base_commit'], head_commit=original['head_commit'])])], model_calls=0, task_repairs=0)
    manifest = dict(repo=repo, task=task, selection='First (repo, numeric PR) among native-prepared exports with positive, clean original controls.',
        eligible_candidates=[c[2] for c in sorted(candidates)], original_task_identity=original['task_content_identity_sha256'],
        prepared_task_identity=identity(repo, task, new_files), base_commit=original['base_commit'], head_commit=original['head_commit'],
        changed_by_native_preparation=changed, unchanged_original_assets=8, metadata_contract_unchanged=True,
        archive_sha256=sha(path), archive_bytes=path.stat().st_size, files=specs,
        expected_f2p=len(json.loads((source/'tests/f2p.json').read_text())), expected_p2p=len(json.loads((source/'tests/p2p.json').read_text())),
        native_probe_sha256=sha(ROOT/'native-inline-probe.json'), source_ledger_sha256=sha(COORDINATOR/'task-execution-ledger.json'),
        public_base_ref=references[0], original_worker_state_refs=sorted(set([original_from, original_attempt['bootstrap_image_id'], *original_attempt['runtime_image_ids']])),
        original_job_id='/exedev/biotasks28-history-'+slug.lower().replace('__','-')+'-001',
        cache_included_in_runtime_package=False, prebuilt_image_included=False, runtime_executed=False, model_calls=0)
    write(ROOT/'cold-worker-control-plan.json', plan)
    write(ROOT/'cold-worker-inputs.json', manifest)
    print(json.dumps({k:manifest[k] for k in ('task','archive_bytes','expected_f2p','expected_p2p','unchanged_original_assets','runtime_executed')}))


if __name__ == '__main__':
    main()
