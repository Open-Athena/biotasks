"""Remote-only native validation driver; not a Harbor/container acceptance run."""
import base64
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import zipfile

ROOT = Path.cwd()
OUT = ROOT / 'validation-results'
OUT.mkdir(exist_ok=True)
CONFIG = json.loads((ROOT / 'validation-config.json').read_text())
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS', 'RAYON_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'


def bounds():
    # Limit each native child to the task's declared memory and CPU budget.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))


def run(label, command):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = time.monotonic()
    with (OUT / f'{label}.stdout.txt').open('w') as stdout, (OUT / f'{label}.stderr.txt').open('w') as stderr:
        child = subprocess.Popen(command, cwd='/app', stdout=stdout, stderr=stderr,
                                 preexec_fn=bounds, start_new_session=True)
        try:
            code = child.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            code = 124
        finally:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    record = {'label': label, 'command': command, 'start': start,
              'seconds': round(time.monotonic() - before, 3), 'exit_code': code,
              'cumulative_children_peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
    print('VALIDATION_STEP ' + json.dumps(record), flush=True)
    return record


steps = []
try:
    package = ROOT / 'package'
    package.mkdir()
    with zipfile.ZipFile(ROOT / 'package.zip') as archive:
        for info in archive.infolist():
            target = (package / info.filename).resolve()
            assert target.is_relative_to(package.resolve())
            archive.extract(info, package)
    data = (ROOT / 'observed-data.csv').read_bytes()
    assert hashlib.sha256(data).hexdigest() == CONFIG['data_sha256']
    Path('/app/data').mkdir(exist_ok=True)
    Path('/app/data/data.csv').write_bytes(data)
    shutil.copytree(package / 'tests', '/tests', dirs_exist_ok=True)
    Path('/tests/data.csv').write_bytes(data)
    shutil.copytree(package / 'solution', '/solution', dirs_exist_ok=True)
    # Parent-authored audit and mutations are separate from the generated package.
    if (ROOT / 'audit.py').exists():
        shutil.copyfile(ROOT / 'audit.py', '/tests/parent_audit.py')
    steps.append(run('oracle', ['bash', '/solution/solve.sh']))
    if steps[-1]['exit_code'] == 0:
        steps.append(run('native-tests', ['python', '-m', 'pytest', '-q', '-o', 'addopts=',
                                        '/tests/test_outputs.py', '--junitxml=' + str(OUT / 'native-tests.xml')]))
        if (ROOT / 'audit.py').exists():
            steps.append(run('parent-audit', ['python', '/tests/parent_audit.py']))
        if (ROOT / 'mutations.py').exists():
            steps.append(run('negative-controls', ['python', str(ROOT / 'mutations.py')]))
    for dirname in CONFIG.get('output_directories', ['results']):
        source = Path('/app') / dirname
        if source.exists():
            for p in source.rglob('*'):
                if p.is_file() and p.stat().st_size < 2_000_000:
                    dest = OUT / 'oracle-artifacts' / dirname / p.relative_to(source)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(p, dest)
finally:
    (OUT / 'steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    files = {}
    for p in OUT.rglob('*'):
        if p.is_file() and p.stat().st_size < 2_000_000:
            files[str(p.relative_to(OUT))] = p.read_text(errors='replace')
    blob = gzip.compress(json.dumps(files).encode())
    encoded = base64.b64encode(blob).decode()
    print('BIO17_ARTIFACT_SHA256 ' + hashlib.sha256(blob).hexdigest(), flush=True)
    for n in range(0, len(encoded), 24000):
        print('BIO17_ARTIFACT_CHUNK ' + encoded[n:n + 24000], flush=True)
    print('BIO17_ARTIFACT_END', flush=True)

if any(step["exit_code"] != 0 for step in steps):
    sys.exit(1)
