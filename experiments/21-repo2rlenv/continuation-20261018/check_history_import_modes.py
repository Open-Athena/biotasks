"""Reproduce private test-package name collisions with tiny synthetic fixtures."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        modules = []
        for package, name in [('io/format', 'format'), ('sequence', 'sequence')]:
            directory = root / 'r2e_tests/skbio' / package / 'tests'
            directory.mkdir(parents=True)
            (directory / '__init__.py').write_text('')
            module = directory / ('test_' + name + '.py')
            module.write_text('def test_fixture():\n    assert True\n')
            modules.append(str(module.relative_to(root)))
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        outcomes = []
        for options in [[], ['--import-mode=importlib']]:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *options, *modules],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=30)
            outcomes.append({'options': options, 'exit_code': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr})
        assert outcomes[0]['exit_code'] == 2, outcomes[0]
        assert 'tests.test_sequence' in outcomes[0]['stdout'], outcomes[0]
        assert outcomes[1]['exit_code'] == 0, outcomes[1]
        assert '2 passed' in outcomes[1]['stdout'], outcomes[1]
        print(json.dumps({'stage': 'synthetic_import_collision_reproduced_and_resolved',
                          'native_repository_tests_executed': False, 'model_calls': 0,
                          'outcomes': outcomes}))


if __name__ == '__main__':
    main()
