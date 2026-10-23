"""Experimental literal-pytest selection; never execute a command here."""
from pathlib import PurePosixPath
import re
import shlex

VALUE_OPTIONS = {'-k', '-m', '--junitxml', '--junit-xml', '--rootdir', '--confcutdir', '--color', '--tb', '--maxfail', '--durations', '-c', '-o', '--override-ini'}
FLAG_OPTIONS = {'-v', '-vv', '-vvv', '-q', '-qq', '-s', '-x', '--disable-warnings', '--strict-markers', '--strict-config', '--showlocals', '--lf', '--ff'}


def select(command, changed_files, *, enabled=False):
    """Return a decision. Unsupported syntax must not be used as a changed-file arm."""
    def result(status, reason, selected=None, targets=None, reduced=False):
        return {'status': status, 'reason': reason, 'command': command if selected is None else selected,
                'targets': targets or [], 'scope_reduced': reduced}
    if not enabled:
        return result('unchanged', 'policy_disabled')
    prefix = 'cd /workspace && '
    body = command[len(prefix):] if command.startswith(prefix) else command
    # Intentionally conservative even inside quotes. This is not a shell parser.
    if any(c in body for c in '\n\r;&|<>`$\\*?[]{}~'):
        return result('unsupported', 'nonliteral_shell_syntax')
    try:
        tokens = shlex.split(body, posix=True)
    except ValueError:
        return result('unsupported', 'invalid_quoting')
    if tokens[:3] in (['python', '-m', 'pytest'], ['python3', '-m', 'pytest']):
        start = 3
    elif tokens[:1] == ['pytest']:
        start = 1
    else:
        return result('unsupported', 'unknown_invocation')
    positions = []
    i = start
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            positions.extend(range(i + 1, len(tokens)))
            break
        option = token.split('=', 1)[0]
        if option in VALUE_OPTIONS:
            if '=' not in token:
                if i + 1 >= len(tokens) or tokens[i + 1].startswith('-'):
                    return result('unsupported', 'missing_option_value')
                i += 1
        elif token in FLAG_OPTIONS:
            pass
        elif token.startswith('-'):
            return result('unsupported', 'unknown_option_arity')
        else:
            positions.append(i)
        i += 1
    targets = [tokens[i] for i in positions]
    if any('::' in t or t.endswith('.py') for t in targets):
        return result('unchanged', 'explicit_file_or_node_scope', targets=targets)

    def safe_path(path):
        return bool(path) and not path.startswith('-') and not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and bool(re.fullmatch(r'[A-Za-z0-9_./-]+', path))

    if any(not safe_path(t) for t in targets):
        return result('unsupported', 'ambiguous_directory_scope')
    paths = list(dict.fromkeys(p for p in changed_files if p.endswith('.py')))
    if not paths:
        return result('unchanged', 'no_python_test_targets', targets=targets)
    if any(not safe_path(p) for p in paths):
        return result('unsupported', 'unsafe_changed_path')
    roots = [PurePosixPath(t) for t in targets]
    if roots and any(not any(PurePosixPath(p).is_relative_to(root) for root in roots) for p in paths):
        return result('unsupported', 'changed_path_outside_recorded_scope')
    # Removing positional directories preserves all recognized flags and values.
    selected_tokens = [t for i, t in enumerate(tokens) if i not in positions]
    selected_tokens.extend(paths)
    selected = (prefix if command.startswith(prefix) else '') + shlex.join(selected_tokens)
    return result('selected', 'explicit_changed_files_policy', selected, paths, True)
