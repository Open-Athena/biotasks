"""Build from a preserved reference bundle and validate saved author candidates.

This reuses recorded repository environments. It restores the
original reference source before building and records a new local bootstrap image.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record

PROFILES = {
    'biopython': {'candidate': 'e4027e396d2357882bc7',
                  'source': 'Bio/SeqUtils/lcc.py', 'seed_prefix': 'Bio/SeqUtils/',
                  'sha256': '5c16386511a8462504aa6cf9e5d8672e93cb8bd79b2a12146bb5442611ed31df'},
    'scikit-bio': {'candidate': '3cd37b06ec9a972757c3',
                   'source': 'skbio/diversity/alpha/_base.py', 'seed_prefix': 'skbio/diversity/alpha/',
                   'sha256': '04401c1c15fd2a94c54a059b624e590e072d4fc5889d3e5dd453e5ce4dcb2a90'},
}


def prepare_context(task, context, *, repo="biopython"):
    profile = PROFILES[repo]
    reference = (task / 'solution/reference.py').read_bytes()
    if hashlib.sha256(reference).hexdigest() != profile["sha256"]:
        raise ValueError('Unexpected pinned reference source')
    shutil.copytree(task / 'environment', context)
    if (context / 'source/.git').exists():
        raise ValueError('Expected exported source without repository metadata')
    (context / 'source' / profile['source']).write_bytes(reference)
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
    return {'repository_profile': repo, 'reference_sha256': profile['sha256'],
            'original_dockerfile_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'validation_dockerfile_sha256': hashlib.sha256((original + extra).encode()).hexdigest(),
            'adaptations': ['Restore original reference source',
                            'Track built environment for native reset/clean validation'],
            'native_validation_executed': False}


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Approved remote execution required')
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', choices=tuple(PROFILES), default='biopython')
    args = parser.parse_args()
    profile = PROFILES[args.repo]
    candidate = profile['candidate']
    original = Path('/work/native/inputs/native/validation/tasks') / candidate / ('swe-smith-' + candidate)
    authored = json.loads(Path('/work/native/candidates.json').read_text())
    if authored['stage'] != 'authoring_only' or not 1 <= len(authored['records']) <= 10:
        raise ValueError('Expected one to ten authored candidates')
    for record in authored['records']:
        path = Path(record['seed']['relative_path'])
        if '..' in path.parts or not str(path).startswith(profile['seed_prefix']):
            raise ValueError('Candidate is outside the declared repository source cohort')
    output = Path('/evidence/native/code-instruct')
    output.mkdir(parents=True, exist_ok=False)
    context = output / 'build-context'
    record = prepare_context(original, context, repo=args.repo)
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
