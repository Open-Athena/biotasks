"""Check the revised submission against a saved reference, without grading it."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from prepare_lcc_independent_controls import CASES, replace_return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.reference.read_text()
    expression = CASES['equivalent_dna_entropy_preserve_legacy'][0]
    revised = replace_return(source, expression)
    original_namespace = {}
    revised_namespace = {}
    exec(compile(source, str(args.reference), 'exec'), original_namespace)
    exec(compile(revised, 'revised-control.py', 'exec'), revised_namespace)
    old = original_namespace['lcc_mult']
    new = revised_namespace['lcc_mult']
    count = 0
    maximum_error = 0.0
    for length in range(1, 5):
        for bases in itertools.product('ACGT', repeat=length):
            sequence = ''.join(bases)
            for window in range(1, length + 1):
                expected, actual = old(sequence, window), new(sequence, window)
                assert len(expected) == len(actual)
                error = max(abs(a - b) for a, b in zip(expected, actual))
                assert error < 1e-12
                maximum_error = max(maximum_error, error)
                count += 1
    legacy_inputs = ['ACNXGTAC', 'QSALTQPASVSGSPGQSITISCTGTSSDVGSYNLVSWYQQHPGKAPKLMIYEGSKRPSGVSNRFSGSKSGNTASLTISGLQAEDEADYYCSSYAGSSTLVFGGGTKLTVL']
    def outcome(function, sequence, window):
        try:
            return ('returned', function(sequence, window))
        except (ValueError, IndexError, ZeroDivisionError) as exc:
            return ('raised', type(exc).__name__, str(exc))

    for sequence in legacy_inputs:
        for window in (1, min(20, len(sequence)), len(sequence)):
            assert outcome(new, sequence, window) == outcome(old, sequence, window)
    assert new('acgt', 4) == [1.0]
    record = {
        'stage': 'local_reference_comparison_not_native_grading',
        'reference_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'derived_source_sha256': hashlib.sha256(revised.encode()).hexdigest(),
        'dna_sequence_window_pairs': count,
        'maximum_absolute_difference': maximum_error,
        'legacy_input_window_pairs': len(legacy_inputs) * 3,
        'legacy_outcomes_exactly_preserved': True,
        'limitation': 'Independent entropy applies to valid unambiguous DNA only; other inputs use the retained native implementation. Seq object variants remain for remote native tests.',
    }
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
