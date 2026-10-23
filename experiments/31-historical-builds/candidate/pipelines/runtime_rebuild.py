"""Opt-in deterministic replay of recorded bootstrap build commands."""
import shlex


def rebuild_script(commands: list[str], *, exported: bool = False) -> str:
    if not commands or any(not c.strip() or '\x00' in c for c in commands):
        raise ValueError('Expected nonempty recorded rebuild commands without NUL')
    # Running a separate shell avoids Bash disabling errexit in a subshell
    # whose status is checked by an `if` or `||` expression.
    script = 'bash -euo pipefail -c ' + shlex.quote('\n'.join(commands))
    if exported:
        # Install a failure verdict before work begins: failed/timed-out builds
        # must not inherit a previous verification's positive reward.
        return (
            'echo 0.0 > /logs/verifier/reward.txt\n'
            'echo \'{"reward":0.0,"resolved":false,"parse_status":"rebuild_incomplete"}\' > /logs/verifier/reward-details.json\n'
            + script + '\nR2E_REBUILD_RC=$?\n'
            + 'if [ "$R2E_REBUILD_RC" -ne 0 ]; then\n'
            + '  echo R2E_REBUILD_FAILED >&2\n  exit "$R2E_REBUILD_RC"\nfi\n'
        )
    return script + '\n'


def reset_test_script(base_commit: str, files: list[str]) -> str:
    """Restore existing test files; remove additions before reapplying tests."""
    # Validate the commit independently: an absent path is normal for added
    # tests, while an invalid commit or Git error must not be ignored.
    lines = ['git rev-parse --verify ' + shlex.quote(base_commit + '^{commit}') + ' >/dev/null || exit $?']
    for path in files:
        if not path or path.startswith('/') or any(p in ('', '.', '..') for p in path.split('/')):
            raise ValueError('Unsafe or non-normalized test patch path')
        quoted = shlex.quote(path)
        base = shlex.quote(base_commit)
        lines += [
            f'R2E_TRACKED=$(git --literal-pathspecs ls-tree -r --name-only {base} -- {quoted}) || exit $?',
            'if [ -n "$R2E_TRACKED" ]; then',
            f'  git --literal-pathspecs checkout {base} -- {quoted} || exit $?',
            'else',
            f'  rm -f -- {quoted} || exit $?',
            'fi',
        ]
    return '\n'.join(lines) + '\n'
