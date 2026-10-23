"""Bounded synthetic parser checks; never grades an original task."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def parser(path):
    spec = importlib.util.spec_from_file_location('parser_' + str(path.parent), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_pytest


def main():
    old = parser(ROOT / 'upstream/log_parsers/pytest_parser.py')
    new = parser(ROOT / 'candidate/pytest_parser.py')
    old_export = parser(ROOT / 'upstream/pipelines/_pr_runtime_verifier.py')
    new_export = parser(ROOT / 'candidate/_pr_runtime_verifier.py')
    fixtures = [
        ('verbose_pass', 'tests/test_x.py::test_a PASSED [25%]', {'tests/test_x.py::test_a': 'PASSED'}),
        ('verbose_fail', 'tests/test_x.py::test_b FAILED [50%]', {'tests/test_x.py::test_b': 'FAILED'}),
        ('summary_error', 'ERROR tests/test_x.py - ImportError: bad', {'tests/test_x.py': 'ERROR'}),
        ('summary_failure', 'FAILED tests/test_x.py::test_b - AssertionError: bad', {'tests/test_x.py::test_b': 'FAILED'}),
        ('skip', 'SKIPPED [1] tests/test_x.py:42 missing dependency', {'tests/test_x.py:42': 'SKIPPED'}),
        ('parameter', 'tests/test_x.py::test_a[FAILED - x] PASSED [100%]', {'tests/test_x.py::test_a[FAILED - x]': 'PASSED'}),
        ('xdist', '[gw2] [ 20%] PASSED tests/test_x.py::test_a', {'tests/test_x.py::test_a': 'PASSED'}),
        ('skip_reason', 'tests/test_x.py::test_a SKIPPED (no package) [100%]', {'tests/test_x.py::test_a': 'SKIPPED'}),
        ('summary_counts', '2 passed, 1 failed in 0.10s', {}),
        ('unittest_footer', 'FAILED (failures=1, errors=1)', {}),
        ('incomplete_line', 'tests/test_x.py::test_a PASS', {}),
        ('empty', '', {}),
    ]
    results = []
    for name, text, expected in fixtures:
        assert old_export(text) == new_export(text) == expected, name
        assert old(text) == new(text) == expected, (name, old(text), new(text))
        # Actual SGR foreground/reset sequences, including styles surrounding IDs/statuses.
        colored = '\x1b[32m' + text.replace(' PASSED', ' \x1b[1;32mPASSED').replace(' FAILED', ' \x1b[31mFAILED') + '\x1b[0m'
        assert new_export(colored) == expected, (name, new_export(colored))
        assert new(colored) == expected, (name, new(colored))
        results.append({'case': name, 'expected': expected,
                        'original_colored': old(colored), 'candidate_colored': new(colored),
                        'original_export_colored': old_export(colored), 'candidate_export_colored': new_export(colored)})
    sequence = 'tests/test_x.py::test_a PASSED [100%]\nFAILED tests/test_x.py::test_a - error'
    assert new(sequence) == {'tests/test_x.py::test_a': 'FAILED'}
    # Removing colors does not establish completion: a timed-out partial log can still parse.
    partial = '\x1b[31mtests/test_x.py::test_a FAILED [1%]\x1b[0m\n[timeout after 600s]'
    assert new(partial) == {'tests/test_x.py::test_a': 'FAILED'}
    # Load exact pure targeting functions without importing/installing the pipeline.
    src = (ROOT / 'upstream/pipelines/pr_runtime.py').read_text()
    tree = ast.parse(src)
    wanted = {'_PYTEST_TARGETABLE_EXT', '_JEST_TARGETABLE_EXT', '_go_packages_from_test_files', 'targeted_test_cmds_for_pr'}
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in wanted)
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets))]
    namespace = {'re': re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pinned_targeting', 'exec'), namespace)
    fn = namespace['targeted_test_cmds_for_pr']
    broad = 'cd /workspace && python -m pytest -v mne/'
    assert fn([broad], ['mne/tests/test_example.py']) == [broad]
    narrow = fn(['cd /workspace && python -m pytest -v'], ['mne/tests/test_example.py'])
    assert narrow == ['cd /workspace && python -m pytest -v mne/tests/test_example.py']
    out = {'scope': 'Synthetic expected-status fixtures and exact pinned targeting functions; no task execution/regrading',
           'fixtures': results, 'native_export_expected_status_parity': True, 'last_write_wins_preserved': True,
           'partial_log_still_parseable_not_acceptable_as_complete': True,
           'broad_command_preserved': broad, 'pathless_command_targeted': narrow,
           'targeting_function_source_sha256': hashlib.sha256(src.encode()).hexdigest(),
           'limitations': ['SGR normalization does not prove runner completion', 'No live MNE result or SAMtools suitability claim',
                           'Broader terminal control sequences intentionally not normalized']}
    (ROOT / 'parser-results.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({'fixtures': len(fixtures), 'all_expected_status_checks_passed': True, 'targeting_checks': 2}))

if __name__ == '__main__':
    main()
