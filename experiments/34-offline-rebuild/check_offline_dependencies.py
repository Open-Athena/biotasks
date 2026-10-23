"""Synthetic planning checks, not a compiled-project or Docker validation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from offline_dependencies import build_plan, inspect_wheel, write_runtime_config

source = b'[project]\nname="target-project"\n[build-system]\nrequires=["setuptools>=80", "wheel"]\nbuild-backend="setuptools.build_meta"\n'
plan = build_plan(source, base_commit='a' * 40)
assert plan['target_distribution'] == 'target-project'
checks = ['static requirements preserved']
def rejected(name, fn):
    try:
        fn()
    except ValueError:
        checks.append(name)
    else:
        raise AssertionError(name)
rejected('target dependency rejected', lambda: build_plan(source.replace(b'setuptools>=80', b'target_project'), base_commit='a'*40))
rejected('direct URL rejected', lambda: build_plan(source.replace(b'setuptools>=80', b'setuptools @ https://example.invalid/pkg.whl'), base_commit='a'*40))
rejected('missing static name rejected', lambda: build_plan(source.replace(b'name="target-project"', b'dynamic=["name"]'), base_commit='a'*40))
with TemporaryDirectory(prefix='biotasks34-wheel-check-') as tmp:
    root = Path(tmp)
    def wheel(filename, name):
        p = root / filename
        with ZipFile(p, 'w') as z:
            z.writestr('example-1.0.dist-info/METADATA', f'Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n')
        return p
    good = wheel('example-1.0-py3-none-any.whl', 'example')
    assert inspect_wheel(good, target_distribution='target-project')['name'] == 'example'
    checks.append('dependency metadata inspected without execution')
    bad = wheel('target_project-1.0-py3-none-any.whl', 'target-project')
    rejected('target wheel rejected', lambda: inspect_wheel(bad, target_distribution='target-project'))
    renamed = wheel('innocent-1.0-py3-none-any.whl', 'target-project')
    rejected('renamed target wheel rejected', lambda: inspect_wheel(renamed, target_distribution='target-project'))
    assert write_runtime_config(root)['PIP_NO_INDEX'] == '1'
    checks.append('offline config disables index')
result = dict(checks=checks, count=len(checks), compiled_fixture_executed=False, remote_jobs=0, model_calls=0)
Path(__file__).with_name('planning-checks.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
