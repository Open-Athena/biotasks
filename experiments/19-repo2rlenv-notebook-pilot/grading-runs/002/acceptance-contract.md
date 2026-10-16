## Acceptance rules for `cluster_marker_genes.csv` (addendum)

Your output is compared against a recorded reference table for the same supplied grouping, on **parsed scientific content**, not on file bytes, row text, or the software that produced it. The reference is read dynamically at grading time; its cluster labels, gene identifiers and row count are taken from the reference file itself, never from any fixed constant. Comparisons are keyed by the stable pair (`cluster`, `gene`) — never by row position, so your row order is checked only against the ordering rule below.

### Required file and format

1. `cluster_marker_genes.csv` must exist directly under your output directory, as a plain CSV whose first line is exactly `cluster,rank,gene,score,pval,pval_adj,log2fc` (same seven columns, same order). Every data row must carry exactly seven fields with no blank (empty or whitespace-only) fields anywhere. A file that is missing, unreadable, has a different header, ragged rows, or blank fields fails all checks (it does not count as a run).
2. Every field of `score`, `pval`, `pval_adj`, `log2fc` must parse as a finite decimal number (plain or scientific notation). `NaN`, `inf`, `-inf`, empty or otherwise non-numeric text fails. Writing a non-zero value with an obviously coarse rounding (e.g. two significant digits) is rejected indirectly, because the numeric comparisons below then fail.
3. `pval` and `pval_adj` must lie in `[0, 1]` (they are two-sided tail probabilities and Benjamini–Hochberg adjusted values).
4. `cluster` must be the supplied label written verbatim, and `gene` the `gene_id` of `gene_identities.csv`. Both are used as exact strings for alignment.
5. `rank` must be a positive integer (a bare integer, no decimals, no exponent).

### Completeness and key alignment

6. The file must contain exactly one row for **every** `(cluster, gene)` pair present in the reference cross product — the complete cluster × tested-gene product and nothing more. Missing pairs, extra pairs, unknown cluster labels, unknown gene identifiers, or duplicated `(cluster, gene)` pairs fail. Per construction the tested gene set is identical for every cluster, so per-cluster row counts must match the reference's counts.

### Ordering and rank

7. Rows must be physically sorted by ascending **numeric** cluster label, then ascending `rank` (e.g. `..., 9, 10, 11, ...`, not lexicographic `1, 10, 11, 2, ...`).
8. Within each cluster, `rank` must be exactly the consecutive integers `1..G`, where `G` is that cluster's number of tested genes. Each rank value appears once per cluster.
9. **Ranking consistency.** Your within-cluster ranking must be a valid descending-score ordering, both against your own reported `score` values and against the reference's scores. Formally, when your rows are taken in your reported rank order, neither your own `score` column nor the reference's `score` for those same genes may increase from one rank to the next by more than the score tolerance (2 × 10⁻⁴, see below). Exact score ties may be broken in any deterministic order, and near-tied genes (scores within the tolerance) may legitimately appear in either order; this tolerance-banded ordering check is what is enforced, so a different but equally valid tie break is accepted.

### Numerical agreement (per `(cluster, gene)` pair)

10. **`score`** — absolute tolerance **2 × 10⁻⁴**. The reference z-statistics were produced by a pipeline whose normalized expression values were held in single precision (float32) before ranking, so cell-level value ties resolve slightly differently than in a full double-precision evaluation. That difference moves the rank sum `W` by a rank unit here and there, which rescales to ≈10⁻⁴ in `z`. Recorded evidence: two fully independent double-precision implementations of the stated definitions agree with the reference to at most 1.05 × 10⁻⁴ absolute on every one of the 398,259 rows, and with each other to at most 6.7 × 10⁻⁵. The acceptance value 2 × 10⁻⁴ is roughly twice the largest observed discrepancy, while real deviations (tie-corrected or continuity-corrected variance, per-cluster instead of pooled normalization, wrong reference group, shuffled cells) produce errors many orders of magnitude larger and are rejected.
11. **`pval`** — relative tolerance **1 × 10⁻²** (fail when |a−b| > 0.01 · min(|a|,|b|)), because the tail probability `p = 2·(1−Φ(|z|))` has relative sensitivity ≈ |z| per unit of z, and |z| reaches ~86 here. With the 10⁻⁴-scale z noise above, the induced relative error stays below about 1%. Independent recomputations agree to at most 2.3 × 10⁻³ relative.
12. **`pval` underflow equivalence.** A reported `0` and any value **≤ 1 × 10⁻³⁰³** are treated as equivalent: such tails come from |z| ≳ 37, where double-precision evaluation legitimately underflows to zero in one implementation while remaining representable in another, and where a z difference of the score-tolerance scale moves the tail across many orders of magnitude. Above that zone a 0 against a positive reference value is a failure, not an equivalence. Note that `pval_adj` values are `m/j`-scaled, which keeps them well inside this zone when they come from such tails.
13. **`pval_adj`** — same rule as `pval`: relative tolerance 1 × 10⁻² with the same 0/underflow equivalence zone. The adjustment must be Benjamini–Hochberg across the whole tested gene universe of the cluster (never a reported subset): omitting the adjustment, Bonferroni-correcting, or adjusting over a top-k subset moves most values far outside tolerance.
14. **`log2fc`** — absolute tolerance **1 × 10⁻⁴**. The reference's stabilized effect sizes were stored in single precision (relative error ~6 × 10⁻⁸ on the mean-derived quantity, absolutely ≤ ~2 × 10⁻⁶ on the reported values); the two independent double-precision recomputations agree with the reference to 1.93 × 10⁻⁶. A 50× margin covers this noise while still rejecting any genuine error (e.g. dropping the `1e-9` stabilizers, swapping cluster and rest means, using log10) by orders of magnitude.

### What is not compared

15. File bytes, CSV quoting style, trailing newline conventions, and number formatting width (beyond rule 2). Two outputs that differ only in such serialization details are equally valid, provided the parsed content satisfies the rules above.
16. No cluster is checked for "biological correctness" — the supplied grouping is a fixed computational input, and only the marker analysis conditional on it is graded.

