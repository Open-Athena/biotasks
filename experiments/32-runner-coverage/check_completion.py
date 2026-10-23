"""Synthetic executor outcomes through exact upstream/candidate validation logic."""
import ast
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def load(name, path):
    tree = ast.parse(path.read_text())
    # Avoid optional package installation: only external repo2rlenv imports are stubbed.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module and n.module.startswith('repo2rlenv'))]
    module = type(sys)(name)
    sys.modules[name] = module
    spec = importlib.util.spec_from_file_location(name + '_parser', ROOT / 'upstream/log_parsers/pytest_parser.py')
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    module.parse_logs = lambda cmds, text, language=None: parser.parse_pytest(text)
    module.DockerSandbox = object
    exec(compile(tree, str(path), 'exec'), module.__dict__)
    module._fetch_base_commit = lambda *args, **kwargs: True
    return module


@dataclass
class Result:
    stdout: str
    exit_code: int = 0
    stderr: str = ''

    def truncated(self, max_chars):
        return self.stdout + self.stderr


class ScriptedSandbox:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def exec(self, command, timeout):
        self.calls += 1
        return self.responses.pop(0)


def log(status):
    return f'R2E_START_TEST_OUTPUT\ntests/test_x.py::test_fix {status} [50%]\ntests/test_x.py::test_stable PASSED [100%]\nR2E_END_TEST_OUTPUT\n'


def main():
    baseline = load('original_validation', ROOT / 'upstream/pipelines/pr_runtime_validate.py')
    candidate = load('candidate_validation', ROOT / 'candidate/pr_runtime_validate.py')
    pre, post = log('FAILED'), log('PASSED')
    cases = [
        ('complete_pair', Result(pre), Result(post), 'verified'),
        ('pre_timeout_with_marker', Result(pre, 124), Result(post), 'failed'),
        ('post_timeout_with_marker', Result(pre), Result(post, 124), 'failed'),
        ('pre_missing_end', Result(pre.replace('R2E_END_TEST_OUTPUT\n', '')), Result(post), 'failed'),
        ('post_missing_end', Result(pre), Result(post.replace('R2E_END_TEST_OUTPUT\n', '')), 'failed'),
        ('missing_start', Result(pre.replace('R2E_START_TEST_OUTPUT\n', '')), Result(post), 'failed'),
        ('stage_failed_with_marker', Result(pre, 2), Result(post), 'failed'),
    ]
    rows = []
    for name, a, b, expected in cases:
        outcomes = {}
        for label, module in [('baseline', baseline), ('candidate', candidate)]:
            sandbox = ScriptedSandbox([a, b])
            out = module.validate_pr(sandbox=sandbox, base_commit='a' * 40,
                                    patch='synthetic source patch', test_patch='synthetic test patch',
                                    test_cmds=['pytest -v'], language='python')
            outcomes[label] = {'status': out.status, 'reason': out.reason,
                               'f2p': out.fail_to_pass, 'p2p': out.pass_to_pass, 'calls': sandbox.calls}
        assert outcomes['baseline']['status'] == 'verified', (name, outcomes)
        assert outcomes['candidate']['status'] == expected, (name, outcomes)
        if expected == 'verified':
            assert outcomes['candidate'] == outcomes['baseline']
        rows.append({'case': name, **outcomes})
    (ROOT / 'completion-results.json').write_text(json.dumps({'scope': 'Synthetic sandbox results through exact validation logic with real pinned pytest parser; no Docker/test execution or original reward changes', 'cases': rows}, indent=2)+'\n')
    print(json.dumps({'cases': len(rows), 'unsafe_synthetic_acceptances_rejected': len(rows) - 1, 'complete_pair_preserved': True}))

if __name__ == '__main__':
    main()
