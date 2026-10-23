"""Model-free Docker transport/timeout probe; owns only labeled disposable containers."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import tarfile
import urllib.request
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
OWNER = os.environ['BIOTASKS_PROBE_RUN_ID']
assert OWNER in {'biotasks30-transport-001', 'biotasks30-transport-002'}
TOOLS = ROOT / 'probe-tools'
LABEL = 'org.open-athena.biotasks.owner=' + OWNER
OWNED = []
REPORT = {'scope': 'Real Docker synthetic transport probe, no repository tasks/models/builds', 'rows': [], 'cleanup': {}}


def docker(*args, timeout=30, check=True):
    return subprocess.run(['docker', *args], text=True, capture_output=True, timeout=timeout, check=check)


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def cleanup():
    for name in OWNED:
        info = docker('inspect', name, check=False)
        if info.returncode == 0:
            record = json.loads(info.stdout)[0]
            assert record['Config']['Labels'].get('org.open-athena.biotasks.owner') == OWNER
            docker('rm', '-f', name)
    remaining = docker('ps', '-aq', '--filter', 'label=' + LABEL).stdout.strip()
    REPORT['cleanup'] = {'owned_containers_absent': not bool(remaining), 'created': OWNED,
                         'host_mounts': False, 'images_created_or_deleted': False}
    assert not remaining


def interrupted(signum, frame):
    raise RuntimeError('probe interrupted by signal ' + str(signum))


def prepare_cli():
    pins = json.loads((ROOT / 'docker-tool.json').read_text())
    TOOLS.mkdir(exist_ok=False)
    path = TOOLS / 'docker.tgz'
    total = 0
    with urllib.request.urlopen(pins['docker_url'], timeout=60) as response, path.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            assert total <= 100 * 1024**2
            output.write(chunk)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pins['docker_sha256']
    with tarfile.open(path) as archive:
        member = archive.getmember('docker/docker')
        assert member.isfile() and member.size < 100 * 1024**2
        (TOOLS / 'docker').write_bytes(archive.extractfile(member).read())
    (TOOLS / 'docker').chmod(0o755)
    path.unlink()
    os.environ['PATH'] = str(TOOLS) + os.pathsep + os.environ['PATH']
    REPORT['docker_cli_archive_sha256'] = pins['docker_sha256']


def main():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    prepare_cli()
    assert not docker('ps', '-aq', '--filter', 'label=' + LABEL).stdout.strip(), 'Existing owned handle; do not duplicate'
    # Use a cached official base only. Missing image is an explicit prerequisite failure.
    img = json.loads(docker('image', 'inspect', 'python:3.12-slim').stdout)[0]
    REPORT['image_id'] = img['Id']
    REPORT['image_repo_digests'] = img.get('RepoDigests', [])
    modules = [('baseline', load('original_docker', 'original_docker.py')),
               ('candidate', load('candidate_docker', 'candidate_docker.py'))]
    for label, module in modules:
        name = OWNER + '-' + label
        OWNED.append(name)
        cid = docker('run', '-d', '--rm', '--name', name, '--label', LABEL,
                     '--cpus', '1', '--memory', '512m', '--pids-limit', '64',
                     '--network', 'none', img['Id'], 'sleep', '540').stdout.strip()
        info = json.loads(docker('inspect', name).stdout)[0]
        assert info['HostConfig']['NanoCpus'] == 1000000000
        assert info['HostConfig']['Memory'] == 512 * 1024**2
        assert info['HostConfig']['NetworkMode'] == 'none' and not info['Mounts']
        sandbox = module.DockerSandbox(cid, '/unused', 'linux/amd64')
        checks = [
            ('quoting', "printf '%s' 'αβ $HOME $(false) `false`'", 0, 'αβ $HOME $(false) `false`'),
            ('stdin_eof', "read -r value; printf '<%s>' \"$value\"", 0, '<>'),
            ('exit_trap', "trap 'printf end' EXIT; printf begin; exit 7", 7, 'beginend'),
            ('cwd_file', "mkdir -p /work-probe; cd /work-probe; printf exact > evidence; cat evidence", 0, 'exact'),
        ]
        for case, command, status, output in checks:
            r = sandbox.exec(command, timeout=5)
            assert r.exit_code == status and r.stdout == output, (label, case, r)
            REPORT['rows'].append({'transport': label, 'case': case, 'passed': True, 'exit_code': r.exit_code})
        payload = ('αβ literal $() `not-run`\n' * 40000)
        command = "cat <<'R2E_PAYLOAD' | sha256sum\n" + payload + 'R2E_PAYLOAD\n'
        try:
            r = sandbox.exec(command, timeout=10)
        except OSError as exc:
            assert label == 'baseline' and exc.errno == 7
            REPORT['rows'].append({'transport': label, 'case': 'large_payload', 'errno': 7})
        else:
            assert label == 'candidate' and r.exit_code == 0
            assert r.stdout.split()[0] == hashlib.sha256(payload.encode()).hexdigest()
            REPORT['rows'].append({'transport': label, 'case': 'large_payload', 'exit_code': r.exit_code,
                                   'payload_bytes': len(payload.encode()), 'exact_sha256': True})
        r = sandbox.exec('while :; do :; done', timeout=0.2)
        assert r.exit_code == 124
        # PID1 is sleep; observer is Python. Any remaining Bash is the timed-out command.
        scan = "import pathlib,json; out=[]\nfor p in pathlib.Path('/proc').iterdir():\n if p.name.isdigit():\n  try:\n   c=(p/'comm').read_text().strip()\n   if c=='bash': out.append(int(p.name))\n  except (FileNotFoundError,ProcessLookupError,PermissionError): pass\nprint(json.dumps(out))"
        pids = json.loads(docker('exec', cid, 'python', '-c', scan).stdout)
        REPORT['rows'].append({'transport': label, 'case': 'timeout', 'client_exit_code': r.exit_code,
                               'bash_processes_remaining_inside_owned_container': pids,
                               'remote_command_terminated_by_client_timeout': not bool(pids)})
        docker('rm', '-f', name)
    REPORT['completed'] = True


if __name__ == '__main__':
    started = time.time()
    status = 0
    try:
        main()
    except Exception as exc:
        REPORT['completed'] = False
        REPORT['error'] = type(exc).__name__ + ': ' + str(exc)
        status = 1
    finally:
        try:
            cleanup()
        except Exception as exc:
            REPORT['cleanup_error'] = type(exc).__name__ + ': ' + str(exc)
            status = 1
        if TOOLS.exists():
            shutil.rmtree(TOOLS)
        REPORT['tool_files_removed'] = not TOOLS.exists()
        REPORT['elapsed_seconds'] = time.time() - started
        (ROOT / 'probe-result.json').write_text(json.dumps(REPORT, indent=2)+'\n')
        print('BIOTASKS30_RESULT=' + json.dumps(REPORT), flush=True)
    raise SystemExit(status)
