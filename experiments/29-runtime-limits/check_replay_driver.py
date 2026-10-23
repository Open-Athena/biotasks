"""Check the source-bound smoke/git orchestration without Docker or network."""
import importlib.util
import json
import logging
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('replay_driver', ROOT / 'replay_scanpy.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ns = {}
m.load_functions(ROOT / 'upstream/auth.py', {'auth_clone_url'}, ns)
url = 'https://github.com/scverse/scanpy.git'
assert ns['auth_clone_url'](url, None) == url

class Fake:
    def __init__(self, codes):
        self.codes = iter(codes)
        self.calls = []

    def exec(self, command, timeout=300):
        self.calls.append((command, timeout))
        code = next(self.codes)
        return SimpleNamespace(exit_code=code, ok=code == 0, stdout='OK' if code == 0 else '', stderr='')

cases = []
for codes, expected, count in [([0, 0], True, 2), ([2, 0], False, 2), ([0, 1, 0], True, 3)]:
    fake = Fake(codes)
    space = {'sandbox': fake, 'outcome': SimpleNamespace(test_cmds=['test-command']),
             'logger': logging.getLogger('fixture'), '_emit': lambda *a: None}
    m.load_post_checks(ROOT / 'upstream/bootstrap/runner.py', space)
    assert space['smoke_ok'] == expected and len(fake.calls) == count
    assert fake.calls[0] == ('test-command', 300) and fake.calls[1][1] == 10
    if count == 3:
        assert fake.calls[2][1] == 180
    cases.append({'codes': codes, 'smoke_passed': expected, 'calls': count})
report = {'status': 'passed', 'scope': 'Exact original AST smoke/git branches with synthetic sandbox; not Docker or biological validation',
          'public_clone_url_unchanged': True, 'cases': cases, 'model_calls': 0, 'remote_jobs': 0}
(ROOT / 'replay-driver-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
