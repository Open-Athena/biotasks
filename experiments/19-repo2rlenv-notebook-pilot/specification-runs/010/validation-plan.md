Private validation plan (not solver-visible). Reward: binary; every justified scientific check must pass.

## A. Endpoint → check map

**E1 `cell_clusters_umap.csv`**
1. Schema per §4.1 of the brief; row set keyed by `cell_id` is unique and equals the reference cell set; `sample` matches per cell.
2. `leiden`, `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`: align each column's labels to the reference by an optimal label bijection (Hungarian matching on the contingency table), then require exact per-cell membership equality.
3. `cell_type_lvl1`: exact per-cell string match against the reference lineages (no bijection; the notebook's fixed dictionary is the definition). Missing/empty values where the reference has a lineage fail.
4. `umap_1`,`umap_2`: compute the optimal similarity alignment (translation, rotation, optional reflection, single scale — Procrustes) to the reference coordinates; require max and RMS residual ≤ `τ_umap`.

**E2 `rank_genes_groups_leiden_res_0.50.csv`**
1. Schema per §4.2; (group, names) unique; the group set equals the categories of the submitted `leiden_res_0.50` column; every filtered gene appears exactly once per group (row count = groups × genes).
2. Rank structure: within each group, `scores` non-increasing; the multiset of (names, scores, pvals, pvals_adj, logfoldchanges) per group matches the reference after applying the same label bijection as for `leiden_res_0.50`.
3. Values within `τ_score` (relative, float32-magnitude), `τ_p`, `τ_lfc` of the reference.
4. Independent recomputation (see C.5).

**E3 `rank_genes_groups_params.json`**: the six fields and values exactly as in §4.3.

## B. Calibration measurements (before release; no thresholds are invented now)

- **Repeatability:** run the reference pipeline ≥ 3 times in the pinned environment; record the maximum run-to-run deviation of scores, p-values, log-fold changes and the Procrustes-aligned UMAP residual. Expected ≈ 0; any non-zero drift sets the noise floor.
- **Portability:** run the pinned pipeline on a second platform and with different thread counts (numba/OpenBLAS) to measure benign numerical spread (PCA sign conventions, summation order). `τ_score`, `τ_p`, `τ_lfc`, `τ_umap` are set as the observed maximum spread plus a safety factor, subject to every wrong-method control in C.3 failing with clear margin (controls must not fall within the tolerance).
- **Tie-order audit:** quantify how many genes per group share exactly equal scores in the reference, confirming that C.4's tie-reordering alternative is non-trivial and that value-keyed comparison (not row-order equality) is required.

## C. Required executable controls (planned, not yet run)

1. **Reference passes:** the archived reference outputs pass all checks in A.
2. **Missing/empty fail:** an empty or absent E1/E2/E3, or a run producing only a subset of endpoints, fails.
3. **Wrong-method controls (each must fail):**
   - filtering: `min_genes=200` or `min_cells=5` (different row set → E1 fails);
   - normalization: `target_sum=1e4` (log1p values shift → E2 scores/`logfoldchanges` fail; record whether E1 partition is also affected — if a control turns out non-consequential for E1, keep it for E2 only and pick an additional E1 control);
   - feature selection: HVG without `batch_key` or with `n_top_genes=5000` (different embedding/clustering → E1 fails);
   - neighbors: `n_neighbors=30` (different graph → E1 fails);
   - clustering: default solution at resolution 0.5, or the resolution loop with `n_iterations=2` instead of to-stability, or leidenalg (RBConfiguration) flavor (partitions/labels differ → E1/E2 fail);
   - annotation: lineage labels swapped between two non-Erythroid lineages across cells (E1 `cell_type_lvl1` fails);
   - UMAP: `min_dist=0.1` or random 2-D coordinates (Procrustes residual > `τ_umap`);
   - DE: `method="t-test"` (statistic differs), `corr_method="bonferroni"` (`pvals_adj` differ), ranking by `|score|` or ascending (monotonicity fails), `groupby="leiden"` (group-set mismatch), top-5-genes-only table (row count fails).
4. **Allowed alternatives must pass (representation-only):**
   - reference E1/E2 with all four cluster columns and the E2 `group` labels renamed by a consistent bijection, `cell_type_lvl1` and all other per-cell values left unchanged;
   - reference UMAP rotated, reflected, translated and uniformly scaled;
   - E1 rows shuffled; E2 group blocks reordered; E2 rows reordered among exactly tied scores.
5. **Independent recomputation from public inputs (portability evidence, without reading reference outputs):** an independently written script reads the two h5 files, rebuilds Steps 1-2 and 4 (read, gex filter, dedup, concatenate, filter) to recover the cell set and gene set, then — taking the submitted cluster assignment from E1 — recomputes the Wilcoxon `z`, two-sided normal p-values, Benjamini–Hochberg `pvals_adj` and the `expm1`-mean log2 fold changes with scipy/statsmodels, and compares them to E2. This validates the DE layer end-to-end independently of scanpy. **Constraint:** recomputing the normalized matrix plus all groups from scratch exceeds the 120 s verifier budget (the reference full pipeline runs ~148 s), so the verifier either (a) recomputes the DE statistics for a stratified sample of genes within budget, or (b) the full independent comparison is executed once at task construction and archived, with the verifier performing the cheap key-space and tolerance checks. This constraint is reported, not silently weakened: if neither option is implemented, the portability claim for E2 stays unvalidated.
6. **No-op detection:** a submission that copies reference files unchanged cannot be distinguished by content checks; scoring still requires the pipeline to run within the sandbox (the harness enforces execution, not this plan).

## D. Unverifiable internal procedures (recorded, not claimed)

The QC annotation (Step 3), Scrublet doublet scoring (Step 5), the raw-count layer, HVG flags, PCA internals and the neighbor graph are internal by design: no intermediate exports are added, so the endpoints cannot distinguish a run that skipped an inert step (Scrublet is provably inert for the endpoints: it operates on copies and writes only the two obs columns). Their faithful execution is instructed in the brief but not verified; no check in A is weakened to compensate.

## E. Policy notes

- `solver_timeout_seconds=600` remains provisional per `task_policy` and may be revisited before solver execution; the reference completed in 147.5 s with peak child RSS 4.9 GiB against the 8 GiB / 4-CPU / offline envelope, so the workflow fits.
- Verifier budget 120 s (see C.5 constraint).
- Binary reward: all checks in A plus all controls in C.1-C.4 must pass; a failed control or alternative leaves that claim unvalidated.
