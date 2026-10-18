"""Install the pinned Marin runtime and execute frozen parity controls remotely."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REVISION = '45a044387ccd95ab698b4a592056aadaff961540'


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Authorized remote worker required')
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((args.inputs / 'manifest.json').read_text())
    assert manifest['marin_revision'] == REVISION and manifest['model_calls'] == 0
    for name, row in manifest['files'].items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        file = args.inputs / relative
        assert file.stat().st_size == row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest() == row['sha256']
    repo = Path('/work/marin')
    repo.mkdir()
    with (args.output / 'marin-setup.log').open('w') as log:
        for command in [
            ['apt-get', 'update'],
            ['apt-get', 'install', '-y', '--no-install-recommends', 'build-essential', 'python3-dev'],
            ['git', 'init', str(repo)],
            ['git', '-C', str(repo), 'remote', 'add', 'origin', 'https://github.com/marin-community/marin.git'],
            ['git', '-C', str(repo), 'fetch', '--depth=1', 'origin', REVISION],
            ['git', '-C', str(repo), 'checkout', '--detach', 'FETCH_HEAD'],
            ['uv', 'sync', '--frozen', '--no-dev', '--package', 'marin-taskcompendium', '--python', '3.12.3', '--project', str(repo)],
        ]:
            subprocess.run(command, stdout=log, stderr=log, timeout=1800, check=True)
    actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == REVISION
    with (args.output / 'runtime.log').open('w') as log:
        result = subprocess.run([str(repo / '.venv/bin/python'), '/work/native/check_pr_marin_parity.py', '--inputs', str(args.inputs), '--output', str(args.output)], stdout=log, stderr=log, timeout=4800)
    (args.output / 'process-result.json').write_text(json.dumps({'marin_revision': actual, 'returncode': result.returncode}) + '\n')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
