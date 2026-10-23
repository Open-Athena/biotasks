"""Actual pinned/candidate exec methods; local Bash adapter, NOT a Docker test."""
from __future__ import annotations
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    real_run = module._run
    calls = []

    def local_adapter(args, *, timeout=600, input_text=None):
        # Assert actual Docker argv shape, then run its shell on this host.
        expected = ['docker', 'exec']
        assert args[:2] == expected
        pos = 2
        interactive = args[pos] == '-i'
        if interactive:
            pos += 1
        assert args[pos:pos + 3] == ['synthetic-container', 'bash', '-lc']
        assert len(args) == pos + 4
        assert interactive == (input_text is not None)
        calls.append({'argv_max_bytes': max(len(x.encode()) for x in args),
                      'stdin_bytes': len((input_text or '').encode()),
                      'timeout': timeout})
        return real_run(['/bin/bash', *args[pos + 2:]], timeout=timeout,
                        input_text=input_text if interactive else '')

    module._run = local_adapter
    return module, calls


def main():
    baseline, old_calls = load('transport_original', 'upstream/bootstrap/docker.py')
    candidate, new_calls = load('transport_candidate', 'candidate/docker.py')
    old = baseline.DockerSandbox('synthetic-container', '/unused', 'linux/amd64')
    new = candidate.DockerSandbox('synthetic-container', '/unused', 'linux/amd64')
    rows = []
    cases = {
        'empty': '',
        'quotes_unicode': "printf '%s\\n' 'literal $HOME `false` $(false) αβ'",
        'trailing_newlines': "printf '%s\\n' retained\n\n\n",
        'stdin_eof': "read -r value; printf '<%s>\\n' \"$value\"",
        'heredoc': "cat <<'BOUNDARY'\n$HOME `false` $(false) quoted ' \" αβ\nBOUNDARY\n",
        'pipefail': "set -o pipefail; false | cat",
        'explicit_exit': "printf out; printf err >&2; exit 17",
        'trap_exit': "trap 'printf cleanup' EXIT; printf before; exit 7",
        'function': "f() { printf '%s' \"$1\"; }; f 'two words'",
        'errexit': "set -e; false; printf should-not-run",
        'nounset': "set -u; printf '%s' \"${__definitely_unset_for_r2e_probe}\"",
        'initial_status': "printf '%s' \"$?\"",
        'login_shell': "shopt -q login_shell; printf '%s:%s' \"$?\" \"$0\"",
    }
    with tempfile.TemporaryDirectory(prefix='biotasks30-shell-') as tmp:
        cases['cwd_persists_inside_command'] = (
            f"cd {shlex.quote(tmp)}; pwd; printf content > probe; cat probe")
        for name, command in cases.items():
            a, b = old.exec(command, timeout=3), new.exec(command, timeout=3)
            assert (a.exit_code, a.stdout) == (b.exit_code, b.stdout), (name, a, b)
            # Shell diagnostic prefixes differ because the candidate uses eval.
            if name != 'nounset':
                assert a.stderr == b.stderr, (name, a.stderr, b.stderr)
            rows.append({'case': name, 'exit_code': b.exit_code,
                         'stdout_sha256': hashlib.sha256(b.stdout.encode()).hexdigest(),
                         'baseline_candidate_match': True})
        payload = ('αβ literal $() `not-run` \' \"\n' * 40000)
        command = "cat <<'R2E_PAYLOAD' | sha256sum\n" + payload + 'R2E_PAYLOAD\n'
        try:
            old.exec(command, timeout=5)
        except OSError as exc:
            assert exc.errno == errno.E2BIG
            old_error = exc.errno
        else:
            raise AssertionError('Expected actual original Linux argument limit')
        b = new.exec(command, timeout=5)
        expected = hashlib.sha256(payload.encode()).hexdigest()
        assert b.exit_code == 0 and b.stdout.split()[0] == expected, b
        rows.append({'case': 'large_literal_payload', 'command_bytes': len(command.encode()),
                     'payload_sha256': expected, 'original_errno': old_error,
                     'candidate_exit_code': b.exit_code, 'exact_payload': True})
        for label, sb in [('baseline', old), ('candidate', new)]:
            r = sb.exec('while :; do :; done', timeout=0.1)
            assert r.exit_code == 124
            rows.append({'case': label + '_timeout', 'exit_code': r.exit_code})
        for label, sb in [('baseline', old), ('candidate', new)]:
            try:
                sb.exec('echo a\x00b')
            except ValueError:
                rows.append({'case': label + '_nul_rejected', 'passed': True})
            else:
                raise AssertionError('NUL must not silently truncate a script')
        new._alive = False
        try:
            new.exec('echo forbidden')
        except candidate.DockerError:
            rows.append({'case': 'dead_sandbox_rejected', 'passed': True})
        else:
            raise AssertionError('Dead sandbox accepted execution')
    result = {'scope': 'Local Bash subprocess comparison of exact exec methods with Docker argv adapter; no Docker daemon, model, PR or container validation.',
              'cases': rows, 'candidate_max_argument_bytes': max(x['argv_max_bytes'] for x in new_calls),
              'candidate_max_stdin_bytes': max(x['stdin_bytes'] for x in new_calls),
              'temporary_paths_removed': not Path(tmp).exists(),
              'sources': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ['upstream/bootstrap/docker.py', 'candidate/docker.py']},
              'limits': ['No Docker daemon tested', 'Inherited Docker exec descendant cancellation not fixed or verified',
                         'BASH_EXECUTION_STRING and shell diagnostic prefixes differ', 'No live PR recovery']}
    (ROOT / 'local-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'cases': len(rows), 'all_passed': True,
                      'max_argument_bytes': result['candidate_max_argument_bytes']}))

if __name__ == '__main__':
    main()
