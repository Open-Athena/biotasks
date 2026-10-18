"""Synthetic asset and graded-result checks; no target execution or services."""
import ast
import copy
import tempfile
from pathlib import Path

from prepare_pr_correctness_controls import assets, controls, portable, source_program
from run_pr_correctness_controls import result_passed


def main():
    for pr in (2630, 5317, 5308):
        for case in ('alternative', 'partial', 'incorrect'):
            ast.parse(source_program(pr, case))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);task=root/'source'
        for name in ('environment','tests','solution'): (task/name).mkdir(parents=True)
        (task/'task.toml').write_text('version="1.0"\n[metadata.repo2env]\ncontent_hash="original"\n[metadata.repo2env.reproducibility]\nimage_tag="fixture-parent"\n')
        (task/'environment/Dockerfile').write_text('FROM fixture-parent\nWORKDIR /workspace\n')
        (task/'environment/docker-compose.yaml').write_text('services: {}\n')
        (task/'instruction.md').write_text('A fixture problem\n')
        (task/'tests/test.sh').write_text('#!/bin/sh\nexit 0\n')
        (task/'solution/patch.diff').write_text('fixture reference\n')
        (task/'solution/solve.sh').write_text('#!/bin/sh\nexit 0\n');(task/'solution/solve.sh').chmod(0o755)
        baseline=root/'Dockerfile';baseline.write_text('FROM python:3.13.2-slim\nWORKDIR /workspace\n')
        before=assets(task);prepared,profile=portable(task,baseline,root/'portable',pr=2630)
        assert assets(task)==before and profile['native_instruction_grader_and_reference_preserved']
        assert 'FROM fixture-parent' not in (prepared/'environment/Dockerfile').read_text()
        assert '/opt/skbio-baseline-extensions/.' in (prepared/'environment/Dockerfile').read_text()
        cases=controls(prepared,root/'controls',pr=2630)
        assert all(assets(Path(row['bundle']),exclude={'solution/solve.sh'})==cases['unchanged_assets'] for row in cases['cases'])
        candidate=Path(cases['cases'][0]['bundle']);(candidate/'tests/test.sh').write_text('changed grader')
        assert assets(candidate,exclude={'solution/solve.sh'})!=cases['unchanged_assets']
    row={'expected_reward':1,'reward':1.0,'returncode':0,'completed':True,'exception_type':None}
    details={'parse_status':'ok','f2p_total':2,'p2p_total':3,'resolved':True,'command_resolved':True}
    assert result_passed(row,details,(2,3))
    for changes in [{'parse_status':'fallback_exitcode'},{'p2p_total':4},{'resolved':False},{'command_resolved':False}]:
        assert not result_passed(row,details|changes,(2,3))
    assert not result_passed(row|{'exception_type':'InfrastructureError'},details,(2,3))
    partial=row|{'expected_reward':'fractional','reward':0.5}
    assert result_passed(partial,details|{'resolved':False,'command_resolved':False},(2,3))
    for reward in [0,1,None]: assert not result_passed(partial|{'reward':reward},details,(2,3))
    print('Asset immutability, nine source-control programs, parser/count/full-credit rejection and fractional-result fixtures passed; target/model/service calls=0.')


if __name__=='__main__':main()
