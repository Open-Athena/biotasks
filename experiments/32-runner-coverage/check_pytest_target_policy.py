"""Bounded selection-contract checks; no shell or biological execution."""
import hashlib
import json
from pathlib import Path
import shlex
from pytest_target_policy import select

ROOT = Path(__file__).resolve().parent
paths = ['mne/tests/test_example.py']
cases = [
    ('recorded_mne', 'cd /workspace && python -m pytest -v mne/', 'selected', 'explicit_changed_files_policy'),
    ('dot', 'pytest .', 'selected', 'explicit_changed_files_policy'),
    ('pathless', 'pytest -v', 'selected', 'explicit_changed_files_policy'),
    ('junit_value', 'pytest --junitxml results/report.xml mne/', 'selected', 'explicit_changed_files_policy'),
    ('junit_equals', 'pytest --junitxml=results/report.xml mne/', 'selected', 'explicit_changed_files_policy'),
    ('quoted_filter', 'pytest -k "alpha or beta" mne/', 'selected', 'explicit_changed_files_policy'),
    ('delimiter', 'pytest -v -- mne/', 'selected', 'explicit_changed_files_policy'),
    ('explicit_file', 'pytest mne/tests/test_other.py', 'unchanged', 'explicit_file_or_node_scope'),
    ('explicit_node', 'pytest mne/tests/test_other.py::test_a', 'unchanged', 'explicit_file_or_node_scope'),
    ('outside', 'pytest other/', 'unsupported', 'changed_path_outside_recorded_scope'),
    ('prefix_collision', 'pytest mn/', 'unsupported', 'changed_path_outside_recorded_scope'),
    ('absolute', 'pytest /workspace/mne/', 'unsupported', 'ambiguous_directory_scope'),
    ('traversal', 'pytest ../mne/', 'unsupported', 'ambiguous_directory_scope'),
    ('unknown_flag', 'pytest --custom-option value mne/', 'unsupported', 'unknown_option_arity'),
    ('missing_value', 'pytest -k', 'unsupported', 'missing_option_value'),
    ('suffix', 'pytest -v; echo complete', 'unsupported', 'nonliteral_shell_syntax'),
    ('pipe', 'pytest -v | tee results.log', 'unsupported', 'nonliteral_shell_syntax'),
    ('redirect', 'pytest > results.log', 'unsupported', 'nonliteral_shell_syntax'),
    ('expansion', 'pytest "$TEST_DIR"', 'unsupported', 'nonliteral_shell_syntax'),
    ('wildcard', 'pytest mne/*', 'unsupported', 'nonliteral_shell_syntax'),
    ('multiline', 'pytest\necho done', 'unsupported', 'nonliteral_shell_syntax'),
    ('invalid_quote', 'pytest "mne/', 'unsupported', 'invalid_quoting'),
    ('unknown_runner', 'python tests.py', 'unsupported', 'unknown_invocation'),
]
rows=[]
for name, command, status, reason in cases:
    off=select(command, paths)
    assert off['command']==command and off['status']=='unchanged'
    actual=select(command, paths, enabled=True)
    assert (actual['status'],actual['reason'])==(status,reason), (name,actual)
    if status!='selected': assert actual['command']==command
    else:
        assert shlex.split(actual['command'])[-1]==paths[0]
        assert actual['scope_reduced'] is True
        if name=='quoted_filter': assert 'alpha or beta' in shlex.split(actual['command'])
        if name=='junit_value': assert 'results/report.xml' in shlex.split(actual['command'])
    rows.append({'case':name,'input':command,'decision':actual})
assert select('pytest mne/', [], enabled=True)['reason']=='no_python_test_targets'
assert select('pytest', ['../tests/test_x.py'], enabled=True)['reason']=='unsafe_changed_path'
assert select('pytest', paths*2, enabled=True)['targets']==paths
out={'scope':'Standalone experimental policy checks, not pipeline integration or task validation',
     'candidate_sha256':hashlib.sha256((ROOT/'pytest_target_policy.py').read_bytes()).hexdigest(),
     'cases':rows,'all_default_commands_byte_preserved':True,'additional_cases':['empty_python_targets','unsafe_changed_path','deduplication'],
     'model_calls':0,'remote_jobs':0,'shell_execution':False,'pipeline_integrated':False}
(ROOT/'pytest-target-policy-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(rows)+3,'passed':True,'pipeline_integrated':False}))
