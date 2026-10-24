"""Bounded input/ownership checks; no Docker or network execution."""
import ast
import hashlib
import json
from pathlib import Path
import tarfile

from harbor_docker_cold import tagged_recipe

ROOT = Path(__file__).resolve().parent


def main():
    for path in ROOT.glob('*.py'):
        ast.parse(path.read_text(), filename=path.name)
    manifest = json.loads((ROOT/'cold-worker-inputs.json').read_text())
    with tarfile.open(ROOT/'inputs-private/cold-worker-inputs.tar.gz') as tar:
        original = tar.extractfile(next(m for m in tar if m.name.endswith('/Dockerfile'))).read()
    effective = tagged_recipe(original, 'test-owner')
    assert effective.replace(b'LABEL biotasks.run=test-owner\n', b'', 1) == original
    assert effective.count(b'LABEL biotasks.run=test-owner\n') == 1
    for invalid in (b'RUN true\n', b'FROM python:3.12\nFROM python:3.11\n'):
        try:
            tagged_recipe(invalid, 'test-owner')
        except AssertionError:
            pass
        else:
            raise AssertionError('Unsupported stage topology accepted')
    source = ROOT.parents[2]/'34/experiments/34-offline-rebuild'
    copied = ['cleanup_owned.py', 'run_existing_controls.py', 'setup_controller.sh', 'control-pins.json']
    assert all((ROOT/name).read_bytes() == (source/name).read_bytes() for name in copied)
    probe = json.loads((ROOT/'native-inline-probe.json').read_text())
    assert hashlib.sha256((ROOT/'native-inline-probe.json').read_bytes()).hexdigest() == manifest['native_probe_sha256']
    case = next(c for c in probe['cases'] if c['repo'] == manifest['repo'])
    for row in manifest['files']:
        name = row['path'].removeprefix('outputs/opencobra__cobrapy/')
        assert case['prepared_inventory'][name]['sha256'] == row['sha256']
    result = dict(syntax_checked=True, ownership_only_verified=True,
        unsupported_stage_topologies_rejected=2, original_helpers_identical=len(copied),
        native_task_files_verified=10, docker_commands=0, model_calls=0)
    (ROOT/'cold-input-checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
