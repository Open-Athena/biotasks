"""Static inspection of a generated package; does not run its code or tests."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

root = Path(__file__).resolve().parents[1]/'runs/20261006-seta-v1-pilot/seta-builder'
checks = []
required = ['instruction.md', 'task.toml', 'environment/Dockerfile', 'solution/solve.sh', 'tests/test.sh', 'tests/test_outputs.py', 'weights.json']
for name in required:
    checks.append({'path': name, 'check': 'required artifact', 'passed': (root/name).is_file()})
for p in sorted(root.rglob('*')):
    if not p.is_file():
        continue
    if p.suffix == '.py':
        try:
            ast.parse(p.read_text())
            checks.append({'path': str(p.relative_to(root)), 'check': 'Python syntax', 'passed': True})
        except SyntaxError as e:
            checks.append({'path': str(p.relative_to(root)), 'check': 'Python syntax', 'passed': False, 'error': str(e)})
    elif p.suffix == '.sh':
        check = subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True)
        checks.append({'path': str(p.relative_to(root)), 'check': 'shell syntax only', 'passed': check.returncode == 0, 'stderr': check.stderr})
    elif p.suffix == '.toml':
        try:
            tomllib.loads(p.read_text())
            checks.append({'path': str(p.relative_to(root)), 'check': 'TOML syntax', 'passed': True})
        except tomllib.TOMLDecodeError as e:
            checks.append({'path': str(p.relative_to(root)), 'check': 'TOML syntax', 'passed': False, 'error': str(e)})
try:
    weights = json.loads((root/'weights.json').read_text())
    checks.append({'path': 'weights.json', 'check': 'numeric nonnegative weights sum to one', 'passed': all(isinstance(x, (int, float)) and x >= 0 for x in weights.values()) and abs(sum(weights.values()) - 1) < 1e-9})
except (OSError, ValueError, TypeError) as e:
    checks.append({'path': 'weights.json', 'check': 'weights parse', 'passed': False, 'error': str(e)})
record = {'kind': 'parent static inspection; not scientific/native validation', 'checks': checks, 'sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'static-inspection.json'}}
(root/'static-inspection.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'passed':sum(c['passed'] for c in checks), 'failed':[c for c in checks if not c['passed']]}))
