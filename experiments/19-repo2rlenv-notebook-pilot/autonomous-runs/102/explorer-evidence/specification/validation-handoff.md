## Input materialization

Solver receives the three already-staged, hash-pinned gzip files at the task-relative paths in the brief: `ENCFF401MQL.bed.gz` (sha256 c0bfc8ded835fdc1f1a06884ffb08f5347a0546c11757f7cc18185b49b9ffcd5), `ENCFF356LFX.bed.gz` (a9d086ce90ca67f933b29adfbff56ea768bbce2ec4b0d51e2d405e5a1d61bb56), `MA0139.1.tsv.gz` (b1bbdac330cfc78c9ac9a826d1ca2bfdb22ec2cc21c789404adc0c11acbd4510). No intermediate or derived inputs are supplied; no new derivation is needed. Both reference artifacts are recorded with full hashes (41d968a3… and 842a5c4b…), 40557 and 40587 rows respectively.

## Proposed comparison rules (to validate executably before finalizing)

**Output 1 (`peaks_with_strongest_motif_blacklist_filtered.csv`)**
- Canonicalize each row: parse `start,end,start_2,end_2` as integers, `fc,pval_2` as floats; map empty fields and `pval_2 == -1` to a canonical "no motif" marker (reference encodes the sentinel as `-1.0` because the chained in-place `replace(-1, np.nan)` fails under pandas 3.1 CoW — trial log, reference.py:84 — while the notebook intended NaN; both encodings denote the same scientific state, so normalization rather than a method prescription).
- Compare canonicalized rows as a **multiset** (row-permutation tolerant); position in this file carries no rank or correspondence meaning. Run an explicit row-permutation probe of the reference to confirm the grader is order-insensitive on this file.
- Exact numeric equality (all values are verbatim decimal strings from the inputs; no arithmetic beyond parsing; no float tolerance assumed — verify parse round-trip, e.g. fc `5.04924`, pval `450.0`).
- Structural checks: exact header `chrom,start,end,fc,chrom_2,start_2,end_2,pval_2,strand_2`; `strand_2 ∈ {+,-,no-motif}`; every fragment lies within its source peak interval; fragments of one peak are disjoint and carry identical `fc`/motif fields; `pval_2` equals the group's maximum overlapping-motif p-value (or sentinel); expected row multiset size equals the reference's (40557, private expectation).

**Output 2 (`motifs_per_peak.csv`)**
- Exact positional sequence match against the reference vector (row i ↔ i-th input peak record); integers. Verify a permuted sequence **fails** — order encodes peak correspondence here, so no permutation probe.

## Pre-finalization checks needed (private measurements, not yet done)

1. Reference biconditional `pval_2 == -1 ⟺ empty chrom_2` (strongly implied: 5765 empty `chrom_2`, 0 empty `pval_2`, min −1.0, printed 0.14 ≈ 5765/40587; not exhaustively scanned). If violated, recast the public wording to "no motif p-value available".
2. Tie incidence: count groups whose maximum-pval set contains multiple distinct motifs (distinct `chrom_2/start_2/end_2/strand_2`). If zero, a lenient "any maximizer" rule is equivalent to the specified first-in-order rule; if nonzero, keep the deterministic rule (the strict rule is already stated publicly and matches `idxmax` first-max semantics over (peak index, motif index) sorted overlap rows).
3. Scan the blacklist input for intervals with `start < 1000`: `bioframe.expand` does not clamp to 0 and `subtract` complements to int64 max, so negative expanded starts are handled by union coverage; if such intervals exist, confirm alternative implementations that clamp agree, or document that the union-coverage wording is the binding rule (it already is).
4. Confirm duplicate-coordinate pooling actually occurs in the inputs (40587 peak records → fewer distinct coordinate groups; reference net effect 40557 rows) so the pooling rule stays in the contract.

## Discriminating incorrect outputs (validation should confirm these fail)

- Inner-join overlap (drops the ~14% motif-less peaks; wrong row counts and missing sentinel rows).
- Per-record assignment without coordinate pooling (row-count mismatch for any duplicated peak coordinates).
- Boundary-inclusive (closed-interval) overlap (inflates counts and admits bookended motifs).
- ±1 kb applied as a distance-from-summit / peak-center filter instead of base-level set subtraction with fragment splitting (drops whole peaks instead of trimming; changes row multiset).
- Not discarding the motif file's first line (shifts counts and, if that motif overlaps a peak, one assignment).
- Restoring `pval_2` to empty instead of −1: must PASS under normalization (legitimate, older-pandas-equivalent behavior).

## Tolerances

None proposed beyond exact numeric equality after parsing plus the −1/empty normalization; if validation finds any parsing-driven float discrepancy (not expected), calibrate then — missing calibration is not a blocker for this draft. Replay evidence (2 byte-identical reruns) shows serialization stability only; comparison rules remain unvalidated until the executable grader passes both a correct reproduction and the incorrect variants above.
