"""Verify the complete selected native PR-diff export and its sole tooling append."""
import hashlib
import json
import re
import tomllib
from pathlib import Path

TOOLING_APPEND=('\n# Solver runtime tooling: installed at build time; learner remains offline.\n'
                'RUN apt-get update && apt-get install -y --no-install-recommends tmux && rm -rf /var/lib/apt/lists/* \\\n'
                '    && tmux -V > /opt/terminus-tool-version.txt\n')
NETWORK_APPEND='\n# Research runtime adaptation: both phases inherit this offline baseline.\n[environment]\nnetwork_mode = "no-network"\n'


def check_task(task:Path,review_path:Path):
    review=json.loads(review_path.read_text())
    if review['stage'] not in ('prepared_for_native_runtime_controls','accepted_for_bounded_similarity_pilot'):
        raise ValueError('Unreviewed PR-diff runtime stage')
    metadata=tomllib.loads((task/'task.toml').read_text())['metadata']['repo2env']
    if metadata['pipeline']!='pr_diff' or metadata['reward_kinds']!=['diff_similarity']:
        raise ValueError('Unexpected native objective')
    if metadata['repo']!=review['repository'] or metadata['ref']!=review['base'] or re.fullmatch(r'[0-9a-f]{40}',review['base']) is None:
        raise ValueError('Frozen repository/base differs')
    files={str(f.relative_to(task)):f for f in task.rglob('*') if f.is_file() or f.is_symlink()}
    if set(files)!=set(review['asset_sha256']) or set(files)!=set(review['runtime_asset_sha256']):
        raise ValueError('PR-diff asset set differs')
    for name,path in files.items():
        if path.is_symlink() or path.stat().st_mode & 0o7777 != review['asset_modes'][name]:
            raise ValueError('Unexpected asset link or permissions')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=review['runtime_asset_sha256'][name]:
            raise ValueError('Runtime asset bytes changed')
        if name=='environment/Dockerfile':
            suffix=TOOLING_APPEND.encode()
            if not data.endswith(suffix):raise ValueError('Unexpected runtime append')
            data=data[:-len(suffix)]
        if name=='task.toml':
            suffix=NETWORK_APPEND.encode()
            if not data.endswith(suffix):raise ValueError('Unexpected network adaptation')
            data=data[:-len(suffix)]
        if hashlib.sha256(data).hexdigest()!=review['asset_sha256'][name]:
            raise ValueError('Native export bytes changed')
    if (task/'environment/docker-compose.yaml').exists() or (task/'tests/Dockerfile').exists():
        raise ValueError('Unreviewed environment structure')
    return review
