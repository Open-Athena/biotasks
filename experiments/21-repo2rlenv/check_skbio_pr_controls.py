"""Offline check of exact native grading-asset retention and control scripts."""
import argparse
import ast
import json
import tempfile
from pathlib import Path

from prepare_skbio_pr_controls import prepare,retained_hashes

parser=argparse.ArgumentParser()
parser.add_argument('--task',type=Path,required=True)
args=parser.parse_args()
with tempfile.TemporaryDirectory() as tmp:
    output=Path(tmp)/'controls'
    records=prepare(args.task,output)
    original=retained_hashes(args.task)
    assert len(records)==5
    for case in records:
        path=Path(case['bundle'])
        assert retained_hashes(path)==original
        if case['case']!='native_reference':
            script=(path/'solution/solve.sh').read_text()
            body=script.split("<<'PYCONTROL'\n",1)[1].rsplit('PYCONTROL\n',1)[0]
            ast.parse(body)
    assert next(x for x in records if x['case']=='e_step_only')['expected_reward'] is None
print('PASS: five controls prepared; native grading/environment/instruction unchanged; generated scripts parse; no execution or model calls')
