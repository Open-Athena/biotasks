"""Portable profiles and explicit source-level controls for three native PR tasks.

Preparation does not execute target code or establish task acceptance. Native
instructions, tests and reference patches remain byte-identical. Controls alter
only their solution script and never write verifier outputs.
"""
import ast
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import tomli_w

SEQ_CONSTRUCTOR = '            lowercase_mask = self._bytes > self._ascii_lowercase_boundary'
SEQ_CONSTRUCTOR_ALT = '            lowercase_mask = np.logical_and(self._bytes >= 97, self._bytes <= 122)'
SEQ_LOWER = '        outbytes[index] ^= self._ascii_invert_case_bit_offset'
SEQ_LOWER_ALT = '        selected = outbytes[index]\n        outbytes[index] = np.where((selected >= 65) & (selected <= 90), selected | 32, selected)'
QCP_CALL = '        (self.rms, self.rot, _) = qcp(coords_ref, coords, self._natoms)'
QCP_SVD = '''        u, singular_values, vt = np.linalg.svd(coords.T @ coords_ref)
        correction = np.eye(3)
        correction[-1, -1] = np.linalg.det(u @ vt)
        self.rot = u @ correction @ vt
        residual = coords @ self.rot - coords_ref
        self.rms = float(np.sqrt(np.sum(residual * residual) / self._natoms))'''


def assets(task, *, exclude=()):
    result = {}
    for file in sorted(Path(task).rglob('*')):
        if file.is_symlink():
            raise ValueError('Unexpected linked task asset')
        relative = file.relative_to(task).as_posix()
        if file.is_file() and relative not in exclude:
            result[relative] = {'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'mode': oct(file.stat().st_mode & 0o777)}
    return result


def source_program(pr, case):
    if pr == 2630:
        path = '/workspace/skbio/sequence/_sequence.py'
        replacements = [(SEQ_CONSTRUCTOR, SEQ_CONSTRUCTOR_ALT)]
        if case == 'alternative':
            replacements.append((SEQ_LOWER, SEQ_LOWER_ALT))
        elif case == 'partial':
            pass
        elif case == 'incorrect':
            replacements = [(SEQ_LOWER, '        return "a" * len(self)')]
        else:
            raise ValueError('Unknown sequence control')
    elif pr == 5317:
        path = '/workspace/Bio/PDB/qcprot.py'
        replacement = QCP_SVD
        if case == 'partial':
            replacement += '\n        self.rms = 0.0'
        elif case == 'incorrect':
            replacement += '\n        self.rot = np.eye(3)'
        elif case != 'alternative':
            raise ValueError('Unknown QCP control')
        replacements = [(QCP_CALL, replacement)]
    elif pr == 5308:
        bodies = {'alternative': 'return hash((self.ref_db, self.ref, self._strand, self._end, self._start))', 'partial': 'return hash((int(self._start), int(self._end), self._strand, self.ref, self.ref_db))', 'incorrect': 'return id(self)'}
        if case not in bodies:
            raise ValueError('Unknown location control')
        method = '    def __hash__(self):\n        ' + bodies[case] + '\n'
        return "import ast\nfrom pathlib import Path\np=Path('/workspace/Bio/SeqFeature.py')\ns=p.read_text()\ntree=ast.parse(s)\ncls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SimpleLocation')\nassert not any(isinstance(n,ast.FunctionDef) and n.name=='__hash__' for n in cls.body)\neq=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__eq__')\nlines=s.splitlines(keepends=True)\nlines.insert(eq.end_lineno," + repr('\n' + method) + ")\ns=''.join(lines)\nast.parse(s)\np.write_text(s)\n"
    else:
        raise ValueError('Unknown frozen PR')
    program = 'import ast\nfrom pathlib import Path\np=Path(' + repr(path) + ')\ns=p.read_text()\n'
    for before, after in replacements:
        program += f'assert s.count({before!r}) == 1\ns=s.replace({before!r},{after!r},1)\n'
    return program + 'ast.parse(s)\np.write_text(s)\n'


def portable(task, baseline, output, *, pr):
    if pr not in (2630, 5317, 5308):
        raise ValueError('Unreviewed PR profile')
    task, baseline, output = Path(task), Path(baseline), Path(output)
    original = assets(task)
    configuration = tomllib.loads((task / 'task.toml').read_text())
    metadata = configuration['metadata']['repo2env']
    tag = metadata['reproducibility']['image_tag']
    marker = 'FROM ' + tag + '\n'
    native_docker = (task / 'environment/Dockerfile').read_text()
    parent = baseline.read_text()
    if native_docker.count(marker) != 1 or sum(line.startswith('FROM ') for line in parent.splitlines()) != 1:
        raise ValueError('Unexpected native/parent Dockerfile')
    cache = 'skbio' if pr == 2630 else 'biopython'
    dockerfile = native_docker.replace(marker, parent.rstrip() + '\n', 1)
    dockerfile += '\n# Restore unchanged parent extensions after the native checkout cleanup.\nRUN cp -a /opt/' + cache + '-baseline-extensions/. /workspace/\n'
    dockerfile += '# Terminal tooling is installed at build time; execution remains offline.\nRUN apt-get update && apt-get install -y --no-install-recommends tmux && rm -rf /var/lib/apt/lists/* && tmux -V > /opt/terminus-tool-version.txt\n'
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(task, output / 'task')
    copied = output / 'task'
    (copied / 'environment/Dockerfile').write_text(dockerfile)
    compose = copied / 'environment/docker-compose.yaml'
    if not compose.is_file():
        raise ValueError('Expected the preserved native compose asset')
    compose.unlink()
    for phase in ('environment', 'agent', 'verifier'):
        configuration.setdefault(phase, {})['network_mode'] = 'no-network'
    configuration['environment'].update(cpus=1, memory_mb=2048)
    configuration['agent']['timeout_sec'] = 900.0
    metadata['original_content_hash'] = metadata.pop('content_hash', '')
    metadata['original_reproducibility'] = metadata.pop('reproducibility', {})
    metadata['validation_profile'] = 'portable_offline_graded_controls_unvalidated'
    (copied / 'task.toml').write_text(tomli_w.dumps(configuration))
    changed = {'environment/Dockerfile', 'environment/docker-compose.yaml', 'task.toml'}
    assert assets(task, exclude=changed) == assets(copied, exclude=changed)
    profile = {'stage': 'portable_profile_prepared_not_executed', 'pr': pr, 'source_assets': original, 'portable_assets': assets(copied), 'changed_assets': sorted(changed), 'baseline_dockerfile_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(), 'native_instruction_grader_and_reference_preserved': True, 'reward': 'graded f2p_rate times p2p_rate, rounded six decimals', 'limits': ['No runtime result yet.', 'Base-image tag and package/OS indexes remain rebuild dependencies.', 'Native checkout cleanup, followed by explicit parent-extension restoration; no source/test/fixture rewrite.']}
    (output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    return copied, profile


def controls(task, output, *, pr):
    task, output = Path(task), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    fixed = assets(task, exclude={'solution/solve.sh'})
    records = []
    for name, expected in [('baseline', 0), ('native_reference', 1), ('alternative', 1), ('partial', 'fractional'), ('incorrect', 0), ('alternative_repeat', 1)]:
        destination = output / name
        shutil.copytree(task, destination)
        if name != 'native_reference':
            script = '#!/bin/sh\nset -eu\n'
            if name != 'baseline':
                program = source_program(pr, 'alternative' if name == 'alternative_repeat' else name)
                ast.parse(program)
                script += "python3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n'
            (destination / 'solution/solve.sh').write_text(script)
        assert assets(destination, exclude={'solution/solve.sh'}) == fixed
        records.append({'case': name, 'bundle': str(destination), 'expected_reward': expected})
    result = {'stage': 'controls_prepared_not_executed', 'pr': pr, 'unchanged_assets': fixed, 'reward_semantics': 'graded native test correctness; not patch similarity', 'cases': records, 'model_calls': 0}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
