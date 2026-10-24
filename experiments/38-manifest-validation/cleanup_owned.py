"""Remove only one run's Docker resources, leaves first; never rerun generation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request


def cleanup(binary, run):
    records = []
    def command(*args):
        return subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=90)
    def listing(*args):
        result = command(*args)
        result.check_returncode()
        return sorted(set(result.stdout.split()))
    for label in ['biotasks.run=', 'biotasks.controller=']:
        ids = listing('ps', '-aq', '--filter', 'label=' + label + run)
        if ids:
            command('rm', '-f', *ids).check_returncode()
    # Earlier deletions can also remove ancestors; refresh before each pass.
    for attempt in range(32):
        ids = listing('image', 'ls', '-aq', '--no-trunc', '--filter', 'label=biotasks.run=' + run)
        if not ids:
            break
        removed = False
        for image in ids:
            result = command('image', 'rm', '-f', image)
            records.append({'pass': attempt, 'image': image, 'exit_code': result.returncode})
            removed |= result.returncode == 0
        if not removed:
            break
    volumes = listing('volume', 'ls', '-q', '--filter', 'label=biotasks.run=' + run)
    for volume in volumes:
        command('volume', 'rm', volume).check_returncode()
    remaining = {
        'containers': listing('ps', '-aq', '--filter', 'label=biotasks.run=' + run),
        'controllers': listing('ps', '-aq', '--filter', 'label=biotasks.controller=' + run),
        'images': listing('image', 'ls', '-aq', '--no-trunc', '--filter', 'label=biotasks.run=' + run),
        'volumes': listing('volume', 'ls', '-q', '--filter', 'label=biotasks.run=' + run),
    }
    return {'run_id': run, 'removal_attempts': records, 'remaining': remaining,
            'verified_empty': not any(remaining.values())}


def main():
    root = Path(__file__).parent
    pins = json.loads((root / 'pins.json').read_text())
    archive = root / 'docker.tgz'
    with urllib.request.urlopen(pins['docker_url'], timeout=60) as src, archive.open('wb') as dst:
        while chunk := src.read(1024 * 1024): dst.write(chunk)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == pins['docker_sha256']
    binary = root / 'docker'
    with tarfile.open(archive) as bundle:
        binary.write_bytes(bundle.extractfile('docker/docker').read())
    binary.chmod(0o755)
    result = cleanup(binary, os.environ['BIOTASKS_CLEANUP_RUN'])
    result['finished'] = time.time()
    (Path(os.environ['IRIS_OUTPUT_DIR']) / 'cleanup-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    assert result['verified_empty'], 'Owned resources remain; never remove unrelated descendants'


if __name__ == '__main__': main()
