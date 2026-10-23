"""Capture an offline-cache receipt immediately after build, before task teardown.

Creates a stopped, resource-bounded, networkless container. Never starts it or
executes image code. This changes evidence collection only, not task behavior.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess


def validate_receipt(receipt):
    plan = receipt['plan']
    assert re.fullmatch('[0-9a-f]{40}', plan['base_commit'])
    assert re.fullmatch('[0-9a-f]{64}', plan['pyproject_sha256'])
    assert plan['target_distribution'] and plan['build_requirements']
    assert receipt['python'] and receipt['platform'] and receipt['wheels']
    seen = set()
    for wheel in receipt['wheels']:
        assert re.sub('[-_.]+', '-', wheel['name'].lower()) != re.sub('[-_.]+', '-', plan['target_distribution'].lower())
        assert wheel['filename'].endswith('.whl') and Path(wheel['filename']).name == wheel['filename']
        assert wheel['filename'] not in seen
        seen.add(wheel['filename'])
        assert re.fullmatch('[0-9a-f]{64}', wheel['sha256'])
        assert 0 < wheel['bytes'] <= 128 * 1024**2
    assert sum(w['bytes'] for w in receipt['wheels']) <= 256 * 1024**2


def capture(real, run_id, image, evidence, run=subprocess.run):
    def docker(*args, check=True):
        return run([real, *args], capture_output=True, text=True, timeout=60, check=check)

    info = json.loads(docker('image', 'inspect', image).stdout)[0]
    assert info['Config']['Labels']['biotasks.run'] == run_id
    assert 'PIP_NO_INDEX=1' in info['Config']['Env']
    ident = info['Id']
    assert re.fullmatch('sha256:[0-9a-f]{64}', ident)
    directory = Path(evidence) / 'dependency-receipts'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (ident.split(':')[1] + '.json')
    temporary = target.with_suffix('.partial')
    assert not temporary.exists(), 'Interrupted receipt copy requires inspection'
    name = run_id + '-receipt-' + ident.split(':')[1][:12]
    created = False
    try:
        docker('create', '--name', name, '--cpus=1', '--memory=128m', '--memory-swap=128m',
               '--network=none', '--label', 'biotasks.run=' + run_id, '--entrypoint', '/bin/true', ident)
        created = True
        docker('cp', name + ':/opt/biotasks-build-cache-receipt.json', str(temporary))
        assert not temporary.is_symlink() and temporary.stat().st_size < 1024**2
        raw = temporary.read_bytes()
        receipt = json.loads(raw)
        validate_receipt(receipt)
        if target.exists():
            assert target.read_bytes() == raw, 'Receipt for immutable image changed'
        else:
            temporary.replace(target)
        return dict(image_id=ident, file=str(target.relative_to(evidence)),
                    sha256=hashlib.sha256(raw).hexdigest(), captured_before_task_start=True)
    finally:
        if temporary.exists():
            temporary.unlink()
        if created:
            docker('rm', name)
