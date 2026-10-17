"""Prepare GC-skew submissions while retaining every native grading asset."""

import argparse
import json
import shutil
from pathlib import Path

from prepare_alpha_mutation_controls import replace_body

SOURCE = 'Bio/SeqUtils/__init__.py'
CASES = {
    'alternative_character_loop': ('''sequence = str(seq.seq if hasattr(seq, 'seq') else seq).upper()
result = []
for start in range(0, len(sequence), window):
    guanine = cytosine = 0
    for nucleotide in sequence[start:start + window]:
        guanine += nucleotide == 'G'
        cytosine += nucleotide == 'C'
    total = guanine + cytosine
    result.append((guanine - cytosine) / total if total else 0.0)
return result''', 1),
    'wrong_single_zero': ('return [0.0]', None),
    'wrong_zero_per_window': ('return [0.0 for _ in range(0, len(seq), window)]', None),
}


def prepare(task, output):
    from repo2rlenv.emitter.bundle import inspect_bundle
    from prepare_skbio_pr_controls import retained_hashes

    identity = inspect_bundle(task)
    if not identity['integrity_passed']:
        raise ValueError('Original native bundle changed')
    contract = json.loads((task/'tests/contract.json').read_text())
    if SOURCE not in contract['submitted_files'] or len(contract['expected_passes']) != 12:
        raise ValueError('Unexpected GC-skew contract')
    if 'Tests.test_SeqUtils.SeqUtilsTests::test_GC_skew' not in contract['expected_passes']:
        raise ValueError('Missing reviewed GC-skew test')
    source = (task/'environment/source'/SOURCE).read_text()
    output.mkdir(parents=True, exist_ok=False)
    assets = retained_hashes(task)
    records = []
    cases = [('baseline', None, 0), ('native_reference', None, 1)]
    cases += [(name, body, reward) for name, (body, reward) in CASES.items()]
    for name, body, reward in cases:
        destination = output/name
        shutil.copytree(task, destination)
        if name == 'baseline':
            script = '#!/bin/sh\nset -eu\n# Retain the original defective source.\n'
        elif body is not None:
            changed = replace_body(source, 'GC_skew', body)
            program = "from pathlib import Path\nPath('/workspace/" + SOURCE + "').write_text(" + repr(changed) + ")\n"
            script = "#!/bin/sh\nset -eu\npython3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n'
        else:
            script = (task/'solution/solve.sh').read_text()
        (destination/'solution/solve.sh').write_text(script)
        assert retained_hashes(destination) == assets
        records.append({'case': name, 'bundle': str(destination), 'expected_reward': reward,
                        'interpretation': 'coverage diagnostic; no pass/fail expectation' if reward is None else 'independent correctness control'})
    manifest = {'stage': 'prepared_unexecuted', 'function': 'GC_skew',
                'source_bundle_hash': identity['bundle_hash'], 'unchanged_assets': assets,
                'cases': records, 'limits': ['Native source, tests and grader retained',
                                           'Incorrect zero-only controls observe native test coverage']}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.task, args.output)
