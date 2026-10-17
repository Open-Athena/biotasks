"""Prepare explicit solution controls for the native PR2633 grader.

These are diagnostic submissions, not generated tasks or blind solver attempts.
Only solution/solve.sh changes; native instruction, environment and grading assets
remain byte-identical. The E-step-only case is a coverage probe, not assumed wrong.
"""
import argparse
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import tomli_w

E_OLD = '        resp /= np.sum(resp, axis=0, keepdims=True)'
M_OLD = '        l1, l2 = numer / denom'
E_SAFE = ('        totals = np.sum(resp, axis=0, keepdims=True)\n'
          '        resp[:] = np.divide(resp, totals, out=np.zeros_like(resp), where=totals != 0)')
M_SAFE = '        l1, l2 = np.divide(numer, denom, out=np.zeros_like(numer), where=denom != 0)'
GROUPING_OLD = '    if idx.size < 2:'
GROUPING_WRONG = '    if idx.size < 0:'
CASES = {
    'baseline': ({}, 0),
    'alternative_masked_division': ({E_OLD:E_SAFE, M_OLD:M_SAFE}, 1),
    'e_step_only': ({E_OLD:E_SAFE}, None),
    'wrong_uniform_responsibilities': ({E_OLD:'        resp[:] = 1.0 / 3.0', M_OLD:M_SAFE}, 0),
}


def retained_hashes(task, *, offline=False):
    result = {}
    for p in sorted(task.rglob('*')):
        if p.is_symlink():
            raise ValueError('Unexpected linked task asset')
        excluded = {'solution/solve.sh'}
        if offline:
            excluded |= {'task.toml', 'environment/docker-compose.yaml'}
        if p.is_file() and str(p.relative_to(task)) not in excluded:
            result[str(p.relative_to(task))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def offline_profile(task):
    path = task / 'task.toml'
    config = tomllib.loads(path.read_text())
    for phase in ('environment', 'agent', 'verifier'):
        config.setdefault(phase, {})['network_mode'] = 'no-network'
    config['environment'].update(cpus=1, memory_mb=2048)
    metadata = config['metadata']['repo2env']
    metadata['original_content_hash'] = metadata.pop('content_hash', '')
    metadata['validation_profile'] = 'offline_runtime_compatibility_unvalidated'
    path.write_text(tomli_w.dumps(config))
    (task / 'environment/docker-compose.yaml').unlink()


def prepare(task, output, *, offline=False, partial=False):
    hashes = retained_hashes(task, offline=offline)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    cases = dict(CASES)
    if partial:
        cases['fixed_underflow_with_grouping_regression'] = (
            {E_OLD:E_SAFE, M_OLD:M_SAFE, GROUPING_OLD:GROUPING_WRONG}, 'fractional',
        )
    for name, (replacements, expected) in cases.items():
        dest = output/name
        shutil.copytree(task, dest)
        if offline:
            offline_profile(dest)
        program = ('from pathlib import Path\n'
                   "p=Path('/workspace/skbio/stats/composition/_ancombc.py')\n"
                   's=p.read_text()\n')
        for before, after in replacements.items():
            program += f'assert s.count({before!r}) == 1\ns=s.replace({before!r},{after!r},1)\n'
        program += 'p.write_text(s)\n'
        (dest/'solution/solve.sh').write_text("#!/bin/bash\nset -eu\npython3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n')
        assert retained_hashes(dest, offline=offline) == hashes
        records.append({'case':name,'bundle':str(dest),'expected_reward':expected,
                        'interpretation':'coverage observation only' if expected is None else 'correctness control'})
    dest=output/'native_reference'
    shutil.copytree(task,dest)
    if offline:
        offline_profile(dest)
    assert retained_hashes(dest, offline=offline) == hashes
    records.insert(1,{'case':'native_reference','bundle':str(dest),'expected_reward':1,'interpretation':'native reference replay'})
    (output/'manifest.json').write_text(json.dumps({'stage':'prepared_unexecuted_controls','offline_profile':offline,'partial_control':partial,'unchanged_assets':hashes,'cases':records},indent=2)+'\n')
    return records


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--offline-profile',action='store_true')
    parser.add_argument('--partial-control',action='store_true')
    args=parser.parse_args()
    prepare(args.task,args.output,offline=args.offline_profile,partial=args.partial_control)
