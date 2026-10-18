# `lcc_mult` returns LCC values scaled by the window size squared instead of normalized scores in [0, 1]

## Summary

`Bio.SeqUtils.lcc.lcc_mult(seq, window)` returns local compositional complexity values that are off the documented normalized entropy scale. In every observed case the returned value is the correct normalized score multiplied by `window**2`, so instead of lying in `[0, 1]` for nucleotide windows, the results grow quadratically with the window size (`60.98...` with `window=8`; `400.0` and `199.31...` with `window=20`). Checksum and GC-fraction computations on the same sequences are correct, so the defect is isolated to the LCC calculation in `lcc_mult`.

## Reproducer

```python
from Bio.SeqUtils.lcc import lcc_mult

# Window spans the whole sequence; letter counts are A=3, C=2, G=2, T=1.
values = lcc_mult('ACGATAGC', 8)
print(values)
# Actual:   [60.98044999134613]
# Expected: [0.9528]  (a single value equal to 0.9528 to four decimal places)

# The first 20 bases contain five each of A, C, G and T, i.e. a window of
# maximal normalized complexity.
values = lcc_mult('ATGCGTATCGATCGCGATACGATTAGGCGGAT', 20)
print(values[0])
# Actual:   400.0
# Expected: 1.0
```

## Actual behavior

- `lcc_mult('ACGATAGC', 8)` returns `[60.98044999134613]`.
- `lcc_mult('ATGCGTATCGATCGCGATACGATTAGGCGGAT', 20)` returns a list whose first element is `400.0`.
- With `window=20` on a longer DNA sequence, the first value returned was `199.3156856932417` where the correct score is `0.4982`.
- Where the exact correct score is computable from the window composition, the returned value is exactly `window**2` times it: `60.98044999134613 = 8**2 x 0.9528195...` and `400.0 = 20**2 x 1.0`; the `199.3156856932417` observation matches the same `20**2 = 400` factor. The mis-scaling is systematic, not data-dependent.
- The number of returned values is unaffected in the observed cases (exactly one value when the window spans the whole sequence); only the magnitudes are wrong.

## Expected behavior

- `lcc_mult(seq, window)` returns one score per window position, `len(seq) - window + 1` values in total: exactly one value when `window == len(seq)`, and 13 values for a 32-base sequence with `window=20`.
- Each score is the normalized entropy of that window's letter frequencies: `-sum(p_i * log4(p_i))` over the letters present in the window (equivalently, the Shannon entropy in bits divided by 2). For nucleotide windows this lies in the closed interval `[0, 1]`:
  - exactly `1.0` for a window with equal counts of A, C, G and T (the first 20 bases of the sequence above);
  - `0.9528` to four decimal places (exact value `0.9528195...`) for `'ACGATAGC'` (counts A=3, C=2, G=2, T=1);
  - `0.0` for a window consisting of one repeated letter.
- The per-window scores must be on the same scale `lcc_simp` uses: the score for a window must agree with the value `lcc_simp` returns for that window's subsequence.
- `lcc_mult` must continue to accept plain strings, `Bio.Seq.Seq`, and `Bio.SeqRecord.SeqRecord` arguments, returning identical values for equivalent sequences.
- `lcc_simp(seq)` - its signature takes only the sequence, with no window argument - currently returns correct values; a fix to `lcc_mult` must leave `lcc_simp`'s signature and returned values unchanged.

Work in `/workspace`. Submit your fix in the existing Python source files under `Bio/SeqUtils`. Preserve the other public behavior. The environment is offline; dependencies are preinstalled. Grading runs the relevant repository tests in a fresh environment, using your submitted source files.
