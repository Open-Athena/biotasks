"""Validate frozen inputs for a no-model history runtime probe, not acceptance."""
import hashlib
import json
import tomllib
from pathlib import Path


def check_task(task: Path, review: Path, *,
               allowed_recipes=('swe_gen', 'swe_next', 'r2e_gym')):
    record = json.loads(review.read_text())
    if record['status'] != 'runtime_probe_only_acceptance_pending':
        raise ValueError('Expected a pending runtime probe review')
    if record['reward']['range'] != [0, 1]:
        raise ValueError('Unexpected history reward range')
    actual = {}
    for path in task.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked runtime task asset')
        if path.is_file():
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            actual[path.relative_to(task).as_posix()] = {
                'sha256': digest, 'mode': path.stat().st_mode & 0o7777}
    if actual != record['assets']:
        raise ValueError('Runtime task bytes, modes, or file set changed')
    config = tomllib.loads((task / 'task.toml').read_text())
    metadata = config['metadata']['repo2env']
    if metadata['bundle_hash'] != record['source_bundle_hash']:
        raise ValueError('Source bundle identity differs')
    if metadata['recipe'] not in allowed_recipes:
        raise ValueError('Unreviewed recipe')
    if metadata['repository'] != 'https://github.com/scikit-bio/scikit-bio':
        raise ValueError('Provider readiness is scoped to scikit-bio')
    if config['verifier']['environment_mode'] != 'separate':
        raise ValueError('Separate verifier required')
    for section in ('environment', 'agent', 'verifier'):
        if config[section]['network_mode'] != 'no-network':
            raise ValueError('Offline runtime required')
    if (task / 'environment/docker-compose.yaml').exists():
        raise ValueError('Unreviewed compose configuration')
