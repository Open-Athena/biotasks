"""Offline check of exact native grading-asset retention and control scripts."""
import argparse
import ast
import json
import tempfile
import tomllib
from pathlib import Path

from prepare_skbio_pr_controls import prepare,retained_hashes,E_OLD,E_SAFE,M_OLD,M_SAFE,GROUPING_OLD,GROUPING_WRONG

parser=argparse.ArgumentParser()
parser.add_argument('--task',type=Path,required=True)
parser.add_argument('--source',type=Path)
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
    offline=prepare(args.task,Path(tmp)/'offline',offline=True)
    for case in offline:
        path=Path(case['bundle'])
        assert retained_hashes(path,offline=True)==retained_hashes(args.task,offline=True)
        config=tomllib.loads((path/'task.toml').read_text())
        assert all(config[phase]['network_mode']=='no-network' for phase in ('environment','agent','verifier'))
        assert not (path/'environment/docker-compose.yaml').exists()
        assert config['metadata']['repo2env']['original_content_hash']

    partial=prepare(args.task,Path(tmp)/'partial',offline=True,partial=True)
    assert len(partial)==6
    for case in partial:
        assert retained_hashes(Path(case['bundle']),offline=True)==retained_hashes(args.task,offline=True)
    assert sum(x['expected_reward']=='fractional' for x in partial)==1
    if args.source:
        source=args.source.read_text()
        for before,after in [(E_OLD,E_SAFE),(M_OLD,M_SAFE),(GROUPING_OLD,GROUPING_WRONG)]:
            assert source.count(before)==1
            source=source.replace(before,after,1)
        ast.parse(source)
print('PASS: native/offline controls plus six-case partial profile prepared; grading/instruction unchanged; generated scripts parse; no execution or model calls')
