"""Bounded synthetic offline-build comparison; run under node resource guard."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from offline_dependencies import build_plan, inspect_wheel, write_runtime_config

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'fixture-results'
OUT.mkdir(exist_ok=True)
plan = build_plan((ROOT/'fixture/pyproject.toml').read_bytes(), base_commit='0'*40)
# The zero SHA identifies only this synthetic fixture, never a historical repo.
env = {k: v for k, v in os.environ.items() if not k.startswith('PIP_')}
env.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_CACHE_DIR='1')
records = []
def run(name, args, child_env, cwd=None):
    start = time.time()
    with (OUT/f'{name}.log').open('w') as log:
        result = subprocess.run(args, env=child_env, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    records.append(dict(name=name, command=args, exit_code=result.returncode, seconds=time.time()-start,
        log_sha256=hashlib.sha256((OUT/f'{name}.log').read_bytes()).hexdigest()))
    return result.returncode
with tempfile.TemporaryDirectory(prefix='biotasks34-compiled-', dir=ROOT/'private') as tmp:
    path = Path(tmp)
    cache = path/'wheels'; cache.mkdir()
    empty = path/'empty'; empty.mkdir()
    source = path/'source'; shutil.copytree(ROOT/'fixture', source)
    venv = path/'venv'
    assert run('prepare', [sys.executable, '-m', 'pip', 'download', '--index-url', 'https://pypi.org/simple',
        '--only-binary=:all:', '--dest', str(cache), *plan['build_requirements']], env) == 0
    wheels = [inspect_wheel(p, target_distribution=plan['target_distribution']) for p in sorted(cache.glob('*.whl'))]
    assert wheels and sum(x['bytes'] for x in wheels) < 20*1024**2
    assert run('venv', [sys.executable, '-m', 'venv', str(venv)], env) == 0
    python = str(venv/'bin/python')
    command = [python, '-m', 'pip', 'install', '-e', '.']
    failed = run('empty-cache', command, env | write_runtime_config(empty), cwd=source)
    assert failed != 0
    failed_log = (OUT/'empty-cache.log').read_text()
    assert 'No matching distribution found for setuptools==80.9.0' in failed_log
    assert run('prepared-cache', command, env | write_runtime_config(cache), cwd=source) == 0
    assert run('compiled-import', [python, '-c', 'import offline_probe; assert offline_probe.answer() == 42; print(offline_probe.__file__)'], env, cwd=path) == 0
    result = dict(fixture='synthetic C extension, no biological data', plan=plan, wheels=wheels, records=records,
        same_install_command_both_arms=True, build_isolation_preserved=True, empty_cache_failed=True,
        prepared_cache_compiled_import=True, operating_system_network_isolation=False,
        limitation='Pip index disabled; no Docker egress-guard or MACS validation in this fixture.',
        model_calls=0, remote_jobs=0)
# Temp paths are retained only as provenance strings; all underlying files removed.
result['owned_temporary_directory_removed'] = not path.exists()
(OUT/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: result[k] for k in ('empty_cache_failed','prepared_cache_compiled_import','owned_temporary_directory_removed')}))
