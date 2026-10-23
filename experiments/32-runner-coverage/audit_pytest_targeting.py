"""Inspect pinned command selection without executing generated shell commands."""
import hashlib
import json
from pathlib import Path
from check_deleted_targets import load

ROOT = Path(__file__).resolve().parent
source = ROOT / 'upstream/pipelines/pr_runtime.py'
selector = load(source)['targeted_test_cmds_for_pr']
paths = ['mne/tests/test_example.py']
cases = [
    ('broad_path', 'python -m pytest -v mne/', 'Explicit scope preserved; replacing it changes measured regression coverage.'),
    ('pathless', 'python -m pytest -v', 'Simple supported pathless command gains the changed file.'),
    ('option_path_value', 'python -m pytest --junitxml results/report.xml', 'Option value is mistaken for an explicit test path; no narrowing occurs.'),
    ('node_id', 'python -m pytest mne/tests/test_other.py::test_example', 'Explicit node selection preserved; replacement would discard that selection.'),
    ('shell_suffix', 'python -m pytest -v; echo complete', 'Changed path is appended to echo, not the pytest invocation.'),
    ('pipeline', 'python -m pytest -v | tee results.log', 'Changed path is appended to tee, not the pytest invocation.'),
    ('quoted_expression', 'python -m pytest -k "alpha / beta"', 'Whitespace tokenization treats the expression slash as a path.'),
    ('root_directory', 'python -m pytest .', 'Dot is not recognized as a path; broad suite remains alongside the added path.'),
]
rows=[]
for name, command, interpretation in cases:
    actual=selector([command],paths)
    expected=command if name in {'broad_path','option_path_value','node_id','quoted_expression'} else command+' '+paths[0]
    assert actual==[expected], (name,actual)
    rows.append({'case':name,'input':command,'selected':actual[0],'interpretation':interpretation})
out={'scope':'Pinned selector executed on synthetic command strings; no shell commands or biological tests executed',
     'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changed_paths':paths,'cases':rows,
     'model_calls':0,'remote_jobs':0,'limits':['This audits selection, not runtime outcomes','No original MNE command or task modified','No coverage or recovery rate inferred']}
(ROOT/'pytest-targeting-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(rows),'all_expected_behaviors_observed':True}))
