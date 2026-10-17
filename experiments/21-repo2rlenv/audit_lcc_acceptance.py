"""Reconcile existing LCC controls and independently check the prompt's arithmetic.

This does not execute the biological library, grade a new submission, or establish
runtime isolation or Marin conversion parity.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path


def audit(task, evidence):
    instruction = (task / 'instruction.md').read_text()
    example = instruction.split('```python\n', 1)[1].split('```', 1)[0]
    assignments = {}
    for node in ast.parse(example).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'seq', 'wsize', 'expected'}:
                assignments[name] = ast.literal_eval(node.value)
    seq, size, expected = (assignments[k] for k in ('seq', 'wsize', 'expected'))
    actual = []
    for start in range(len(seq) - size + 1):
        window = seq[start:start + size]
        fractions = [window.count(base) / size for base in 'ACGT']
        actual.append(-sum(p * math.log(p, 4) for p in fractions if p))
    assert len(actual) == len(expected)
    assert all(abs(x-y) < .0001 and round(x-y, 2) == 0 for x,y in zip(actual, expected))
    controls = {}
    paths = []
    for name in ('biopython-lcc-independent-01', 'biopython-lcc-independent-02', 'biopython-lcc-repeatability-01'):
        path = evidence / name / 'summary.json'
        paths.append(path)
        records = json.loads(path.read_text())['records']
        assert all(row['exception_type'] is None for row in records)
        controls[name] = {row['case']:row['reward'] for row in records}
    assert controls['biopython-lcc-independent-02'] == controls['biopython-lcc-repeatability-01']
    path = evidence / 'biopython-lcc-independent-01/diagnosis/result.json'
    paths.append(path)
    partial = json.loads(path.read_text())
    assert partial['returncode'] == 1 and not partial['passed']
    assert partial['statuses']['Tests.test_SeqUtils.SeqUtilsTests::test_checksum3'] == 'passed'
    return {
        'status':'acceptance_pending_runtime_and_conversion_checks',
        'bundle_identity':'sha256:1a00379124b1cd12878b53b98298bc143ed01eb32f83062265e4df3aaa92cbe6',
        'prompt_sha256':hashlib.sha256((task/'instruction.md').read_bytes()).hexdigest(),
        'prompt_arithmetic':{'windows':len(actual),'maximum_error':max(abs(x-y) for x,y in zip(actual,expected)),
                             'all_native_rounding_comparisons_pass':True},
        'existing_controls':controls,
        'partial_solution':{'classification':'DNA target repaired but legacy protein behavior regressed',
                            'passed_tests':sum(v=='passed' for v in partial['statuses'].values()),
                            'failed_tests':sum(v=='failed' for v in partial['statuses'].values()),
                            'native_binary_reward':0,'new_trial':False},
        'evidence_sha256':{str(p.relative_to(evidence)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'remaining':['Initial learner import and private-path absence checks on exact runtime',
                     'Marin separate-verifier mapping and native reward parity',
                     'Final acceptance decision before one blind solver attempt'],
        'limitations':['Finite native test coverage; supplied DNA example and expected values reduce difficulty',
                       'Uniform windows is ambiguous shorthand; preceding text explicitly means equal base counts',
                       'Partial correctness maps to zero under native binary reward; do not introduce fractional reward',
                       'Deferred report-integrity diagnostic remains unexecuted'],
        'new_model_calls':0,'new_remote_trials':0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = audit(args.task, Path(__file__).resolve().parent/'evidence')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
