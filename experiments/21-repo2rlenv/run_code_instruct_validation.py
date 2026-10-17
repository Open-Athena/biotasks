"""Build from a preserved reference bundle and validate saved author candidates.

This reuses the recorded Biopython environment adaptation. It restores the
original LCC source before building and records a new local bootstrap image.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record

REFERENCE_SHA256 = '5c16386511a8462504aa6cf9e5d8672e93cb8bd79b2a12146bb5442611ed31df'


def prepare_context(task, context):
    reference = (task / 'solution/reference.py').read_bytes()
    if hashlib.sha256(reference).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Unexpected Biopython reference source')
    shutil.copytree(task / 'environment', context)
    if (context / 'source/.git').exists():
        raise ValueError('Expected exported source without repository metadata')
    (context / 'source/Bio/SeqUtils/lcc.py').write_bytes(reference)
    dockerfile = context / 'Dockerfile'
    original = dockerfile.read_text()
    # The native validator resets/cleans HEAD. Track the installed build assets
    # so that this step preserves the environment it is meant to validate in.
    extra = (
        '\nRUN apt-get update && apt-get install -y --no-install-recommends git '
        '&& rm -rf /var/lib/apt/lists/*\n'
        'RUN git init && git config user.name "BioTasks experiment" '
        '&& git config user.email "experiment@example.invalid" '
        '&& git add -f . && git commit -m "Record built validation environment"\n'
    )
    dockerfile.write_text(original + extra)
    return {'reference_sha256': REFERENCE_SHA256,
            'original_dockerfile_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'validation_dockerfile_sha256': hashlib.sha256((original + extra).encode()).hexdigest(),
            'adaptations': ['Restore original LCC implementation',
                            'Track built environment for native reset/clean validation'],
            'native_validation_executed': False}


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Approved remote execution required')
    original = Path('/work/native/inputs/native/validation/tasks/e4027e396d2357882bc7/swe-smith-e4027e396d2357882bc7')
    output = Path('/evidence/native/code-instruct')
    output.mkdir(parents=True, exist_ok=False)
    context = output / 'build-context'
    record = prepare_context(original, context)
    save_record(output / 'bootstrap.json', record)
    image = 'biotasks21-code-instruct-validation:local'
    with (output / 'build.log').open('w') as log:
        result = subprocess.run(['docker', 'build', '-t', image, str(context)],
                                stdout=log, stderr=log, timeout=1200)
    record['build_returncode'] = result.returncode
    save_record(output / 'bootstrap.json', record)
    result.check_returncode()
    record['image_id'] = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
        capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    save_record(output / 'bootstrap.json', record)
    subprocess.run([sys.executable, '/work/native/validate_code_instruct.py',
        '--candidates', '/work/native/candidates.json', '--image', image,
        '--output', str(output / 'validation')], check=True, timeout=4800)
    record['native_validation_executed'] = True
    save_record(output / 'bootstrap.json', record)


if __name__ == '__main__':
    main()
