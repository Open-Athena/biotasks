"""Bounded static package inspection; no generated code is executed."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

root = Path(sys.argv[1]).resolve()
checks = []
for name in ['instruction.md', 'task.toml', 'environment/Dockerfile', 'solution/solve.sh',
             'tests/test.sh', 'tests/test_outputs.py', 'weights.json']:
    checks.append({'check': 'required file', 'path': name, 'passed': (root / name).is_file()})
for p in sorted(root.rglob('*')):
    if not p.is_file():
        continue
    label = str(p.relative_to(root))
    if p.suffix == '.py':
        try:
            ast.parse(p.read_text())
            checks.append({'check': 'Python syntax', 'path': label, 'passed': True})
        except SyntaxError as e:
            checks.append({'check': 'Python syntax', 'path': label, 'passed': False, 'error': str(e)})
    elif p.suffix == '.sh':
        result = subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True, check=False)
        checks.append({'check': 'shell syntax', 'path': label, 'passed': result.returncode == 0,
                       'stderr': result.stderr})
    elif p.suffix == '.toml':
        try:
            tomllib.loads(p.read_text())
            checks.append({'check': 'TOML syntax', 'path': label, 'passed': True})
        except tomllib.TOMLDecodeError as e:
            checks.append({'check': 'TOML syntax', 'path': label, 'passed': False, 'error': str(e)})
try:
    weights = json.loads((root / 'weights.json').read_text())
    checks.append({'check': 'nonnegative weights sum to one', 'passed':
                   all(isinstance(v, (int, float)) and v >= 0 for v in weights.values())
                   and abs(sum(weights.values()) - 1) < 1e-9})
except (OSError, ValueError, TypeError) as e:
    checks.append({'check': 'weight parsing', 'passed': False, 'error': str(e)})
record = {'stage': 'static inspection only', 'checks': checks,
          'file_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(root.rglob('*')) if p.is_file()}}
Path(sys.argv[2]).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'passed': sum(c['passed'] for c in checks),
                  'failed': [c for c in checks if not c['passed']]}))
