"""Probe unmodified native inline preparation on verified frozen exports.

Acquisition and native execution are separate processes. Acquisition downloads
public, hash-bound inputs; native execution forbids networking, subprocesses and
credential-store reads. No Dockerfile command or model call is executed.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parents[2]
BASELINE = TREE.parent/'experiments/28-catalogued-fields/history-wide'
PRIOR = TREE/'31/experiments/31-historical-builds'
COORDINATOR = TREE/'33/experiments/33-unattended-validation'
WORK = ROOT/'inputs-private/native-preparation'
SECRET = re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): dict(bytes=p.stat().st_size, mode=p.stat().st_mode & 0o777, sha256=sha(p))
        for p in sorted(root.rglob('*')) if p.is_file()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def acquire():
    assert not WORK.exists(), 'Preserve prior inputs and results; never overwrite'
    ledger = json.loads((COORDINATOR/'task-execution-ledger.json').read_text())
    tasks = ledger['tasks']
    assert len(tasks) == 83
    public = [t for t in tasks if t['repo'] != 'matchms/matchms']
    profile = json.loads((COORDINATOR/'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    archives = ROOT/'inputs-private/public-phases'
    archives.mkdir(parents=True, exist_ok=True)
    cases = []
    with tempfile.TemporaryDirectory(prefix='native-input-cache-', dir=ROOT/'inputs-private') as td:
        os.environ['HF_XET_CACHE'] = str(Path(td)/'cache')
        from huggingface_hub import HfApi
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars()
        api = HfApi(token=False)
        downloaded = 0
        for repo in sorted({t['repo'] for t in public} | {'macs3-project/MACS'}):
            slug = repo.replace('/', '__')
            manifest_path = BASELINE/'archives'/(slug+'-manifest.json')
            manifest = json.loads(manifest_path.read_text())
            phase = next(r for r in manifest['files'] if r['path'] == 'evidence/phase-artifacts.tar.gz')
            assert phase['bytes'] < 16*1024**2
            if repo == 'macs3-project/MACS':
                archive = PRIOR/'inputs-private/original-phase.tar.gz'
                selected = []
            else:
                archive = archives/(slug+'.tar.gz')
                if not archive.exists():
                    api.download_bucket_files('open-athena/biotasks', [(
                        'research/28-catalogued-fields/2026-10-23/'+sha(manifest_path)+'/evidence/phase-artifacts.tar.gz', archive)],
                        raise_on_missing_files=True, token=False)
                    downloaded += phase['bytes']
                selected = [t for t in public if t['repo'] == repo]
            assert downloaded < 32*1024**2
            assert archive.stat().st_size == phase['bytes'] and sha(archive) == phase['sha256']
            case = WORK/slug
            original = case/'original'
            original.mkdir(parents=True)
            expected = {f"outputs/{slug}/{t['task']}/{f['path']}":(t['task'], f) for t in selected for f in t['original_task_files']}
            member_specs = {r['path']:r for r in phase['members']}
            seen = set()
            caches = []
            total = 0
            with tarfile.open(archive, 'r|gz') as tar:
                for member in tar:
                    total += member.size
                    assert total < 256*1024**2
                    path = PurePosixPath(member.name)
                    assert not path.is_absolute() and '..' not in path.parts
                    cache = member.name.startswith('bootstrap/') and member.name.endswith('/bootstrap.json')
                    if member.name not in expected and not cache:
                        continue
                    assert member.isfile() and member.size < 2*1024**2 and member.name not in seen
                    seen.add(member.name)
                    data = tar.extractfile(member).read()
                    assert len(data) == member.size
                    spec = member_specs[member.name]
                    assert hashlib.sha256(data).hexdigest() == spec['sha256'] and not SECRET.search(data)
                    if cache:
                        target = case/'workspace'/member.name
                        caches.append(dict(member=member.name, sha256=spec['sha256'], path=str(target)))
                    else:
                        task, spec = expected[member.name]
                        assert hashlib.sha256(data).hexdigest() == spec['sha256'] and len(data) == spec['bytes']
                        target = original/task/spec['path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    target.chmod(spec.get('mode', 0o600) if isinstance(spec.get('mode', 0o600), int) else int(spec['mode'], 8))
            assert set(expected) <= seen and len(caches) == 1
            if repo == 'macs3-project/MACS':
                source = TREE/'34/experiments/34-offline-rebuild/inputs-private/offline-controls/outputs/macs3-project__MACS/macs3-project__MACS-742'
                manifest = json.loads((TREE/'34/experiments/34-offline-rebuild/offline-export-manifest.json').read_text())
                for file in manifest['task_files']:
                    rel = file['path'].split('macs3-project__MACS-742/', 1)[1]
                    assert sha(source/rel) == file['sha256']
                shutil.copytree(source, original/'macs3-project__MACS-742')
            cases.append(dict(repo=repo, slug=slug, root=str(case), original=str(original), tasks=[t['task'] for t in selected],
                separate_diagnostic=not bool(selected), phase_sha256=phase['sha256'], manifest_sha256=sha(manifest_path), caches=caches))
    write(ROOT/'native-inputs.json', dict(cases=cases, cohort_tasks=83, public_tasks=len(public),
        restricted_tasks_excluded=83-len(public), downloaded_bytes=downloaded,
        cache_layout='Restore original bootstrap paths under native ./workspace, preserving directory case and file bytes.',
        acquisition_network='Anonymous HF input downloads only; native preparation occurs in a separate process.', model_calls=0))
    print(json.dumps(dict(public_tasks=len(public), restricted_excluded=83-len(public), cases=len(cases), downloaded_bytes=downloaded)))


def without_export_metadata(data):
    result = deepcopy(data)
    meta = result.get('metadata', {}).get('repo2env', {})
    meta.pop('reproducibility', None)
    meta.pop('spec_version', None)
    return result


def probe():
    inputs = json.loads((ROOT/'native-inputs.json').read_text())
    source = PRIOR/'inputs-private/upstream-package'
    acquisition = json.loads((PRIOR/'package-acquisition.json').read_text())
    assert acquisition['revision'] == '27d04ee8203cd5b2f20c3997d13836e5f5b64238'
    for row in acquisition['files']:
        assert sha(source/row['path']) == row['sha256']
    blocked = []
    denied = {str((Path.home()/name).resolve()) for name in ('.docker/config.json', '.git-credentials', '.config/gh/hosts.yml',
        '.codex/secrets/vepbench.env', '.config/coreweave/credentials.env', '.cache/huggingface/token')}

    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
            blocked.append(event)
            raise AssertionError('Native preparation attempted external operation: '+event)
        if event == 'open' and isinstance(args[0], str) and str(Path(args[0]).resolve()) in denied:
            blocked.append('credential_store_open')
            raise AssertionError('Credential-store inspection forbidden in inline probe')

    sys.addaudithook(audit)
    sys.path[:0] = [str(source/'src'), str(PRIOR/'inputs-private/check-deps')]
    from repo2rlenv.registry import integration as native
    assert Path(native.__file__).resolve() == (source/'src/repo2rlenv/registry/integration.py').resolve()
    rows = []
    cwd = Path.cwd()
    for case in inputs['cases']:
        case_root = Path(case['root'])
        prepared = case_root/'prepared'
        assert not prepared.exists(), 'Never overwrite a prior native result'
        shutil.copytree(case['original'], prepared)
        before = inventory(prepared)
        cache = json.loads(Path(case['caches'][0]['path']).read_text())
        lookup_owner, lookup_name, lookup_sha = native._parse_local_tag(cache['image_tag'])
        os.chdir(case_root)
        try:
            recipe, recipe_source = native._load_bootstrap_recipe(cache['image_tag'])
            try:
                value = native.prepare_dataset_for_push(prepared, hf_owner='open-athena', inline_dockerfile=True,
                    pushed_by='biotasks-issue35')
                outcome = dict(state='prepared', result=asdict(value))
            except RuntimeError as error:
                outcome = dict(state='unsupported', error=str(error))
        finally:
            os.chdir(cwd)
        after = inventory(prepared)
        assert set(before) == set(after)
        changes = [name for name in before if before[name] != after[name]]
        if outcome['state'] == 'unsupported':
            assert before == after
        else:
            assert all(name.endswith(('/environment/Dockerfile', '/task.toml')) for name in changes)
            for task in sorted(p.name for p in prepared.iterdir() if p.is_dir()):
                old = tomllib.loads((Path(case['original'])/task/'task.toml').read_text())
                new = tomllib.loads((prepared/task/'task.toml').read_text())
                assert without_export_metadata(old) == without_export_metadata(new)
                assert new['metadata']['repo2env']['reproducibility']['mode'] == 'inline_dockerfile'
        rows.append(dict(repo=case['repo'], separate_diagnostic=case['separate_diagnostic'], tasks=case['tasks'],
            **outcome, cache_image_tag=cache['image_tag'], cache_repo=cache['repo'],
            native_lookup_repo_key=lookup_owner+'__'+lookup_name, preserved_cache_repo_key=Path(case['caches'][0]['member']).parts[1],
            cache_recipe_found=recipe is not None, cache_recipe_source=recipe_source,
            cache_rebuild_commands=len(cache.get('rebuild_cmds') or []),
            clean_recipe_available_from_fields=bool(native._build_clean_recipe(*cache['repo'].split('/', 1), cache)),
            changed_files=changes, original_inventory=before, prepared_inventory=after))
    assert not blocked
    write(ROOT/'native-inline-probe.json', dict(upstream_revision=acquisition['revision'], cases=rows,
        source_acquisition_sha256=sha(PRIOR/'package-acquisition.json'), native_inputs_sha256=sha(ROOT/'native-inputs.json'),
        native_api_executed=True, source_modified=False, network_or_subprocess_operations=blocked,
        credential_store_reads=0, docker_commands_executed=0, model_calls=0, uploads=0,
        scope='Native export preparation only; no build, control result or fresh-worker portability claim.'))
    print(json.dumps([dict(repo=r['repo'], state=r['state'], tasks=len(r['tasks']), cache_recipe_found=r['cache_recipe_found']) for r in rows]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('acquire', 'probe'))
    args = parser.parse_args()
    acquire() if args.action == 'acquire' else probe()
