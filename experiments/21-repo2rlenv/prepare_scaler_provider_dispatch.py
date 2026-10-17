"""Freeze complete no-model SCALER provider inputs without allocating workers."""
import argparse
import hashlib
import json
from pathlib import Path

from run_pr_provider_preflight import check_task

SOURCE_SHA256 = '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'
CODE = ('pr_provider_environment.py', 'run_pr_provider_preflight.py',
        'preserve_author_output.py', 'package_provider_task.py',
        'check_pr_provider_setup.py', 'lcc_provider_environment.py',
        'scaler_provider_environment.py')
TRANSFER = ('acceptance.json', 'task-bundle.tar.gz',
            'task-bundle-manifest.json', 'task-file-modes.json')


def prepare(queue_root, source, output):
    root = Path(__file__).resolve().parent
    queue = json.loads((queue_root / 'queue.json').read_text())
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise ValueError('Runtime source archive changed')
    prepared = []
    # Validate every task before writing the first dispatch package.
    for row in queue['tasks']:
        task_root = queue_root / row['task']
        check_task(task_root / 'roundtrip/task', task_root / 'acceptance.json')
        archive = (task_root / 'task-bundle.tar.gz').read_bytes()
        if hashlib.sha256(archive).hexdigest() != row['archive_sha256']:
            raise ValueError('Task archive changed')
        files = {name: (root / name).read_bytes() for name in CODE}
        files.update({name: (task_root / name).read_bytes() for name in TRANSFER})
        files['glm_remote.py'] = (root / 'run_scaler_provider_remote.py').read_bytes()
        files['repo2rlenv-source.tar.gz'] = source_bytes
        prepared.append((row, files))
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'stage': 'prepared_not_dispatched', 'model_calls': 0,
                'reserved_slots_required': 3, 'probe_seconds': 1800,
                'cleanup_seconds': 240, 'tasks': []}
    for row, files in prepared:
        directory = output / row['task']
        directory.mkdir()
        hashes = {}
        for name, data in files.items():
            (directory / name).write_bytes(data)
            hashes[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        manifest['tasks'].append({'task': row['task'], 'task_id': row['task_id'],
                                  'expected_rewards': {'nop': -1, 'oracle': 1},
                                  'files': hashes})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('queue-root', 'source', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.queue_root, args.source, args.output)))
