"""Prepare QCP correctness submissions, preserving all non-solution assets."""
import ast
import json
import shutil
from pathlib import Path

from prepare_skbio_pr_controls import retained_hashes

CALL = '        (self.rms, self.rot, _) = qcp(coords_ref, coords, self._natoms)'
TRANSLATION = '        self.tran = com_ref - np.dot(com_coords, self.rot)'
SVD = '''        u, singular_values, vt = np.linalg.svd(coords.T @ coords_ref)
        correction = np.eye(3)
        correction[-1, -1] = np.linalg.det(u @ vt)
        self.rot = u @ correction @ vt
        residual = coords @ self.rot - coords_ref
        self.rms = float(np.sqrt(np.sum(residual * residual) / self._natoms))'''
CASES = {
    'baseline': ({}, 0),
    'alternative_svd': ({CALL: SVD}, 1),
    'wrong_translation': ({CALL: SVD, TRANSLATION: '        self.tran = np.zeros(3)'}, 0),
    'wrong_identity_rotation': ({CALL: SVD + '\n        self.rot = np.eye(3)'}, 0),
    'wrong_zero_reported_rms': ({CALL: SVD + '\n        self.rms = 0.0'}, 0),
}


def prepare(task, output):
    from repo2rlenv.emitter.bundle import inspect_bundle
    identity = inspect_bundle(task)
    assert identity['integrity_passed']
    contract = json.loads((task / 'tests/contract.json').read_text())
    assert contract['submitted_files'] == ['Bio/PDB/qcprot.py']
    assert len(contract['expected_passes']) == 9
    assert any(x.endswith('::test_collinear_reference_transformed_rmsd')
               for x in contract['expected_passes'])
    source = (task / 'environment/source/Bio/PDB/qcprot.py').read_text()
    assets = retained_hashes(task)
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for name, (replacements, reward) in CASES.items():
        changed = source
        program = "from pathlib import Path\np=Path('/workspace/Bio/PDB/qcprot.py')\ns=p.read_text()\n"
        for before, after in replacements.items():
            assert changed.count(before) == 1
            changed = changed.replace(before, after, 1)
            program += f'assert s.count({before!r}) == 1\ns=s.replace({before!r},{after!r},1)\n'
        ast.parse(changed)
        program += 'p.write_text(s)\n'
        dest = output / name
        shutil.copytree(task, dest)
        (dest / 'solution/solve.sh').write_text("#!/bin/sh\nset -eu\npython3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n')
        assert retained_hashes(dest) == assets
        cases.append({'case': name, 'bundle': str(dest), 'expected_reward': reward,
                      'interpretation': 'independent correctness control'})
    dest = output / 'native_reference'
    shutil.copytree(task, dest)
    assert retained_hashes(dest) == assets
    cases.insert(1, {'case': 'native_reference', 'bundle': str(dest), 'expected_reward': 1,
                     'interpretation': 'unchanged native reference replay'})
    manifest = {'stage': 'prepared_unexecuted', 'source_bundle_hash': identity['bundle_hash'],
                'reward_contract': 'binary_all_expected_tests_pass',
                'unchanged_assets': assets, 'cases': cases,
                'limits': ['No independent runtime result yet',
                           'One collinear regression and eight existing tests; wider degeneracies untested']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return cases
