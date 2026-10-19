## Measured facts (evidence, not proposals)

- Reference executed successfully: `trial/result.json` (exit 0, 4.8 s, peak child RSS ~550 MiB; pandas 2.3.3 logged one FutureWarning from `df_peaks_maxmotif["pval_2"].replace(-1, np.nan, inplace=True)` — the replace still took effect, since the output has blank pval rows). Single artifact: `ctcf_peaks_maxmotif_clean.csv`, sha256 `8ba2ca...447d`, 40,557 rows, columns `chrom,start,end,fc,chrom_2,start_2,end_2,pval_2,strand_2` (`output-audit.json`).
- Output audit: blank `chrom_2` == blank `pval_2` == 5,765; `pval_2` numeric range 384–1035; output rows are not chromosome-sorted (preview chr19/chr4/chr1 with ascending fc), consistent with the derived ordering semantics.
- Semantics verified in bioframe 0.8.0 source: half-open positive-length overlap (`core/arrops.py:338-354`, `closed=False`); exact-string chromosome grouping (`ops.py:287-303`); null-masked right side for unpaired left rows (`ops.py:510-539`); overlap output sorted by (df1 row index, df2 row index) (`ops.py:549-550`); `expand` pads each side (`ops.py:208-212`); `subtract` = complement overlap, splits peaks, carries non-coordinate columns, drops fully covered intervals, and re-sorts by df1 index labels (`ops.py:477,1251-1338`).
- Input identities pinned in `trial/inputs-before.json`: ENCFF401MQL.bed.gz sha256 `c0bf...ffcd5`; ENCFF356LFX.bed.gz sha256 `a9d0...bb56`; MA0139.1.tsv.gz sha256 `b1bb...4510`.

## Approved scope

- One endpoint table (the whole exported 9-column table; no projection, no added summaries, no invented cutoffs). Public schema = reference columns renamed by position: `chrom↔chrom, start↔start, end↔end, fc↔fc, motif_chrom↔chrom_2, motif_start↔start_2, motif_end↔end_2, motif_pval↔pval_2, motif_strand↔strand_2`.

## Input materialization (proposal)

- Reuse the three trial-staged files unchanged (sha256 above), mounted read-only at the public paths from `candidate/inputs.json`. No derived inputs are needed or supplied; nothing downstream is given away.

## Proposed comparison rules (validate before use; not yet executable-validated)

1. Parse solver and reference CSVs with: `chrom`, `motif_chrom`, `motif_strand` as strings; `start`, `end`, `motif_start`, `motif_end` as nullable integers (blank → null); `fc`, `motif_pval` as float64 (blank → null). Do not compare bytes or raw text: `"384"` vs `"384.0"` and similar decimal spellings must compare equal after parsing.
2. Row count must match; then compare row multisets: canonicalize both tables by sorting on the full row tuple, then compare elementwise with null==null, exact integer equality for coordinates, and numeric comparison of `fc`/`motif_pval`. Expected exactness of parsed floats is a claim to verify (values are decimal passthrough / integer algebra); if any writer differences appear across re-runs or independent writers, measure before setting any tolerance — no epsilon or safety factor is proposed now.
3. Row order is NOT compared (reference order = peaks-file order via `subtract`'s index-label re-sorting; audit preview confirms non-chrom-sorted output).
4. Boundary behavior to check: a peak portion exactly 1000 bp away from a blacklist interval (abutting the expanded region) is retained, since abutting half-open intervals share no base.

## Checks to run before finalizing the draft

- **Tie incidence and tie-break necessity:** count peaks whose maximizer is tied, and build reference variants with (a) last-row tie-break and (b) leftmost-motif-coordinate tie-break. If variants differ from the reference output, the file-order tie-break requirement is distinguishing; if variants coincide, the rule is inert and may be relaxed. Do not assume.
- **Duplicate peak coordinates:** check whether any (chrom,start,end) appears more than once in ENCFF401MQL (and whether duplicates carry different fc). If none, the "distinct peak interval" grouping in the public spec exactly equals reference behavior; if present, the merged-row/fc-selection semantics must be re-specified before release.
- **Missing motif pval:** confirm the motif track has no rows lacking `pval`, and that no peak's maximizer lacks `pval` (equal blank counts for `chrom_2`/`pval_2` in the audit already support this for the final output). If such a case exists, the public "blank motif fields" wording must be reconciled with the reference's quirk of reporting motif coordinates with blank pval in that case.
- **Negative controls (must fail grading):** filter-before-assignment; closed-interval (abutting) overlap; no 1 kb expansion; dropping whole peaks near blacklist instead of trimming/splitting; dropping peaks without motifs; minimum instead of maximum `pval`; using motif `score` or peak `-log10p` instead of motif `pval`; reversed tie-break; 'chr'-stripping chromosome normalization.
- **Invariant checks (cheap graders):** every output peak sub-interval lies within its original peak span and avoids the expanded blacklist; split rows of one peak share fc/motif fields; motif intervals of assigned rows overlap the original peak span.
- **Reference environment pin:** keep the reference program on pandas 2.3.3 (trial lockfile retained); the chained-assignment replace would silently no-op on pandas 3.x and turn blank pvals into −1. Reference re-runs must reproduce the artifact hash. Solver receives no pandas-version constraint; grader parses values.

## Unvalidated assumptions

- Exact-after-parse numeric equality for `fc`/`motif_pval` (no tolerance calibrated).
- Absence of tied maximizers needing the tie-break in practice (measure; rule stays specified regardless).
- Absence of duplicate peak coordinates and of missing motif `pval` rows (measure).
- `semantic_fidelity_validated` is false in all provided evidence; the above rules remain proposals until executed against the reference output and the negative controls. No cross-output dependencies exist (single deliverable).
