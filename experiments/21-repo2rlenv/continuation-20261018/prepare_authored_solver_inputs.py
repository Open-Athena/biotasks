"""Restore exact admitted authored profiles, preserving private build contexts."""

import hashlib
import json
import shutil
from pathlib import Path

from audit_robbins_evidence import inventory


def restore(evidence, admission, destination):
    manifest = json.loads((evidence / 'control-manifest.json').read_text())
    storage = json.loads((evidence / 'canonical-task-storage.json').read_text())
    assert admission['candidate_id'] == manifest['candidate_id']
    assert admission['blind_solver_attempts'] == 0
    source = evidence / storage['complete_native_task']
    assert inventory(source) == manifest['native_assets']
    destination.mkdir(exist_ok=False)
    task = destination / 'task'
    shutil.copytree(source, task)
    for name in storage['profile_deleted_assets']:
        (task / name).unlink()
    for name in storage['profile_changed_assets']:
        assert name == 'task.toml'
        shutil.copyfile(evidence / 'profile-delta' / name, task / name)
    actual = inventory(task)
    assert actual == manifest['profile_assets']
    sha = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
    assert sha == admission['portable_asset_manifest_sha256']
    dockerfile = (task / 'environment/Dockerfile').read_text()
    assert 'install -y --no-install-recommends tmux' in dockerfile
    assert (task / 'tests/Dockerfile').is_file()
    item = {'task_id': admission['task_id'], 'repository': admission['repository'],
            'route': admission['route'], 'independently_admitted': True,
            'admitted_asset_manifest_sha256': sha, 'task_assets': actual,
            'admission_artifact_prefix': admission['artifact_prefix'],
            'blind_attempt_limit': 1, 'no_prior_blind_attempt': True,
            'separate_verifier_context_preserved': True, 'runtime_task_assets_changed': False}
    (destination / 'trial-inputs.json').write_text(json.dumps(item, indent=2) + '\n')
    return {'task_id': admission['task_id'], 'unit': destination.name,
            'route': admission['route'], 'repository': admission['repository'],
            'admitted_asset_manifest_sha256': sha, 'prior_blind_attempts': 0,
            'separate_verifier_context_preserved': True, 'asset_count': len(actual)}
