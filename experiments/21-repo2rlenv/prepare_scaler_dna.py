"""Prepare a declared custom biological-algorithm family for the native SCALER route."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
seed = root/'seeds/scaler-dna-edit-v1'
family = {
    'name': 'Synthetic DNA-string edit distance',
    'logic_description': 'Two independent synthetic strings use the DNA alphabet A, C, G, T. Compute the minimum number of single-character insertions, deletions, and substitutions needed to transform first into second. Each operation costs one; matching characters cost zero. Reordering, transpositions, reverse complements, and affine gap penalties are not operations in this problem. These strings are algorithm fixtures, not observed biological samples or a model of biological evolution.',
    'generate_testcase': (seed/'generator.py').read_text(),
    'params': {'length': {'base': 1, 'min': 4}},
    'difficulty_dict': {str(x): x for x in (2, 4, 6, 8, 10, 12)},
    'solutions': {'solution': [(seed/'reference.py').read_text()], 'language': [3]},
    'output_type': 'number',
    'instruction': 'Return one nonnegative integer: the exact minimum edit cost.',
}
path = seed/'families.json'
path.write_text(json.dumps({'synthetic_dna_edit_distance': family}, indent=2)+'\n')
profile = {
    'stage': 'custom_family_prepared_not_executed_remotely',
    'pipeline': 'reasoning_synth', 'recipe': 'scaler',
    'source': {'kind': 'family', 'path': 'seeds/scaler-dna-edit-v1/families.json'},
    'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'options': {'target': 3, 'max_candidates': 10, 'seed': 24,
                'difficulties': [2, 4, 6, 8, 10, 12], 'samples_per_difficulty': 2},
    'input_origin': 'Wholly synthetic uniformly sampled strings over ACGT; custom experiment-authored family, not an upstream released fixture or observed sequence.',
    'protocol': 'Native SCALER expansion/export and -1/+1 grading; no generation model calls. Preserve native export metadata and this separate custom-input provenance.',
    'split_group': 'scaler-dna-edit-v1',
    'independent_family_count': 1,
    'limitations': ['Difficulty means string-length scaling only; empirical solver difficulty unmeasured.',
                    'Instances share one algorithm and must not be represented as independent scientific problems.',
                    'Native containers, baseline/reference, independent grading and blind solver remain unexecuted.'],
}
(root/'scaler-dna-profile.json').write_text(json.dumps(profile, indent=2)+'\n')
print('Prepared one custom synthetic family; no model or worker calls.')
