"""Produce a separately identified cache-enabled task; preserve original assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(original, original_plan, image, destination):
    assert re.fullmatch(r'sha256:[a-f0-9]{64}', image), 'Bind actual reconstruction image digest'
    assert not destination.exists(), 'Never overwrite a task variant'
    plan = json.loads(original_plan.read_text())
    assert len(plan['repositories']) == 1
    repo = plan['repositories'][0]
    assert len(repo['tasks']) == 1
    task = repo['tasks'][0]
    prefix = Path('outputs')/repo['slug']/task['task']
    expected = {str(Path(f['path']).relative_to(prefix)): f for f in task['original_files']}
    assert set(expected) == {str(f.relative_to(original)) for f in original.rglob('*') if f.is_file()}
    for name, spec in expected.items():
        f = original/name
        assert not f.is_symlink() and sha(f) == spec['sha256'] and f.stat().st_size == spec['bytes']
    dependency = json.loads((ROOT/'macs-base-dependency-plan.json').read_text())
    shutil.copytree(original, destination)
    dockerfile = destination/'environment/Dockerfile'
    text = dockerfile.read_text()
    assert text.count('\nFROM ') == 1 and text.splitlines()[1].startswith('FROM ')
    lines = text.splitlines(keepends=True)
    lines[1] = 'FROM '+image+'\n'
    command = ['python', '/opt/biotasks-build-tools/prepare_build_cache.py', '--base-commit', dependency['base_commit'],
        '--pyproject-sha256', dependency['pyproject_sha256']]
    appendix = ('\n# Opt-in #34 preparation: retain original checkout/scrub and runtime guard.\n'
        'COPY offline_dependencies.py prepare_build_cache.py /opt/biotasks-build-tools/\n'
        'RUN '+json.dumps(command)+'\n'
        'ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/biotasks-build-wheels PIP_DISABLE_PIP_VERSION_CHECK=1\n')
    dockerfile.write_text(''.join(lines)+appendix)
    for name in ['offline_dependencies.py', 'prepare_build_cache.py']:
        shutil.copy2(ROOT/name, destination/'environment'/name)
    changes = []
    inventory = []
    for f in sorted(destination.rglob('*')):
        if f.is_file():
            rel = str(f.relative_to(destination))
            digest = sha(f)
            if rel not in expected or digest != expected[rel]['sha256']:
                changes.append(rel)
            inventory.append(dict(path=str(prefix/rel), bytes=f.stat().st_size, sha256=digest, mode=oct(f.stat().st_mode & 0o777)[2:]))
    assert changes == ['environment/Dockerfile','environment/offline_dependencies.py','environment/prepare_build_cache.py']
    task['original_files'] = inventory
    plan['scope'] = 'Separate offline-build-cache candidate; original verifier/tests/patch/egress guard unchanged'
    plan['task_repairs'] = 0
    manifest = dict(image_id=image, changed_files=changes, unchanged_original_files=9,
        original_plan_sha256=sha(original_plan), dependency_plan_sha256=sha(ROOT/'macs-base-dependency-plan.json'),
        task_files=inventory, model_calls=0, controls_executed=False)
    return plan, manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--original-plan', type=Path, required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    plan, manifest = prepare(args.original, args.original_plan, args.image, args.destination)
    (ROOT/'offline-control-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (ROOT/'offline-export-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
