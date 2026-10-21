"""Rebuild the saved upstream Dockerfile verbatim; no bootstrap agent or repairs."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    recipe = Path('/work/bootstrap/saved/Dockerfile')
    metadata = json.loads(recipe.with_name('bootstrap.json').read_text())
    assert recipe.read_text() == metadata['dockerfile_reconstruction']
    context = Path('/work/reconstruction-context')
    real = os.environ['BIOTASKS_REAL_DOCKER']
    run = os.environ['BIOTASKS_RUN_ID']
    report = {
        'started': time.time(), 'repo': metadata['repo'], 'ref': metadata['ref'],
        'recipe_sha256': hashlib.sha256(recipe.read_bytes()).hexdigest(),
        'original_image_digest': metadata['image_digest'],
        'image_tag': metadata['image_tag'], 'llm_calls': 0,
        'method': 'Verbatim upstream transcript Dockerfile, built from pinned repository checkout',
        'limitation': 'Original image was deleted; unpinned base/packages may drift on reconstruction',
    }
    destination = Path('/work/evidence/reconstruction.json')
    destination.write_text(json.dumps(report, indent=2) + '\n')
    try:
        subprocess.run(['git', 'clone', '--no-checkout', '--depth', '1',
                        'https://github.com/' + metadata['repo'] + '.git', str(context)],
                       check=True, timeout=300)
        subprocess.run(['git', '-C', str(context), 'fetch', '--depth', '1', 'origin', metadata['ref']],
                       check=True, timeout=300)
        subprocess.run(['git', '-C', str(context), 'checkout', '--detach', metadata['ref']],
                       check=True, timeout=120)
        assert subprocess.check_output(['git', '-C', str(context), 'rev-parse', 'HEAD'], text=True).strip() == metadata['ref']
        command = [real, 'build', '--force-rm', '--cpu-period=100000', '--cpu-quota=150000',
                   '--memory=6g', '--memory-swap=6g', '--network=iris-egress',
                   '--label', 'biotasks.run=' + run, '--tag', metadata['image_tag'],
                   '-f', str(recipe), str(context)]
        report['command'] = command
        environment = os.environ.copy()
        environment['DOCKER_BUILDKIT'] = '0'
        result = subprocess.run(command, env=environment, check=False, timeout=2700)
        report['exit_code'] = result.returncode
        result.check_returncode()
        report['rebuilt_image'] = json.loads(subprocess.check_output(
            [real, 'image', 'inspect', metadata['image_tag']]))[0]
        for command in [
            ['python', '--version'],
            ['/workspace/.venv/bin/python', '--version'],
            ['/workspace/.venv/bin/pip', 'freeze'],
        ]:
            # Read-only provenance; no package installation or smoke repair.
            name = 'target-packages.txt' if command[-1] == 'freeze' else 'target-versions.txt'
            with (destination.parent / name).open('a') as output:
                subprocess.run([real, 'run', '--rm', '--cpus=1', '--memory=6g', '--memory-swap=6g',
                                '--network=none', '--label', 'biotasks.run=' + run,
                                metadata['image_tag'], *command],
                               stdout=output, stderr=subprocess.STDOUT, check=False, timeout=60)
    finally:
        report['finished'] = time.time()
        destination.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
