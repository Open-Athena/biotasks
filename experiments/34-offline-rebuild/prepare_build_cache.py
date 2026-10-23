"""Trusted image-build step; resolve only declared binary build dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from offline_dependencies import build_plan, inspect_wheel


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-commit', required=True)
    p.add_argument('--pyproject-sha256', required=True)
    args = p.parse_args()
    source = Path('/workspace/pyproject.toml').read_bytes()
    assert hashlib.sha256(source).hexdigest() == args.pyproject_sha256
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert commit == args.base_commit
    plan = build_plan(source, base_commit=commit)
    cache = Path('/opt/biotasks-build-wheels')
    cache.mkdir(exist_ok=False)
    env = {k: v for k, v in os.environ.items() if not k.startswith('PIP_')}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_CACHE_DIR='1')
    subprocess.run([sys.executable, '-m', 'pip', 'download', '--index-url', 'https://pypi.org/simple',
        '--only-binary=:all:', '--dest', str(cache), *plan['build_requirements']], env=env, check=True, timeout=180)
    files = sorted(cache.iterdir())
    assert files and all(f.suffix == '.whl' for f in files)
    assert sum(f.stat().st_size for f in files) <= 256*1024**2
    wheels = [inspect_wheel(f, target_distribution=plan['target_distribution']) for f in files]
    receipt = dict(plan=plan, wheels=wheels, python=sys.version, platform=platform.platform(),
        preparation='base-declared build requirements only; binary wheels; no target-project installation',
        runtime_network_guard='unchanged task compose; pip uses local cache only')
    Path('/opt/biotasks-build-cache-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('BIOTASKS_BUILD_CACHE='+json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
